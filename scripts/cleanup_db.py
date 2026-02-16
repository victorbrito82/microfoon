#!/usr/bin/env python3
"""
Database cleanup script to remove duplicates and trash entries.
Duplicates are identified by:
1. FIRST: Group by (original_filename + date) - since each USB import session restarts REC numbering
2. THEN: Exact match (same file size AND transcript content)
3. FINALLY: Similar match (similar file size within 10% AND similar transcript >85%)
"""
import os
import sys
import sqlite3
import argparse
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# Add parent directory to path to import microfoon modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.progress import track

console = Console()

DB_PATH = Path(__file__).parent.parent / "microfoon.db"
RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"

# Similarity thresholds
TRANSCRIPT_SIMILARITY_THRESHOLD = 0.85  # 85% similar
FILE_SIZE_TOLERANCE = 0.10  # Within 10%


def get_file_size(stored_filename):
    """Get file size in bytes, return None if file doesn't exist."""
    if not stored_filename:
        return None
    file_path = RECORDINGS_DIR / stored_filename
    if file_path.exists():
        return file_path.stat().st_size
    return None


def text_similarity(text1, text2):
    """Calculate similarity ratio between two texts (0.0 to 1.0)."""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.strip(), text2.strip()).ratio()


def file_size_similar(size1, size2, tolerance=FILE_SIZE_TOLERANCE):
    """Check if two file sizes are similar within tolerance."""
    if size1 is None or size2 is None:
        return False
    if size1 == 0 or size2 == 0:
        return size1 == size2
    ratio = min(size1, size2) / max(size1, size2)
    return ratio >= (1 - tolerance)


def extract_date_from_stored_filename(stored_filename):
    """
    Extract date from stored filename.
    Format: YYYYMMDD_HHMMSS_originalname.ext
    Returns: YYYYMMDD string or None if not found
    """
    if not stored_filename:
        return None
    # Match pattern like: 20260215_224026_REC001.WAV
    match = re.match(r'(\d{8})_\d{6}_', stored_filename)
    if match:
        return match.group(1)
    return None


def find_duplicate_groups(records):
    """
    Find groups of duplicate records using:
    1. FIRST: Group by (original_filename + date) - strongest indicator
       Since each USB import session restarts REC numbering, the combination is unique
    2. THEN: Apply exact matching on remaining records
    3. FINALLY: Apply similarity matching on remaining records
    Returns list of groups, where each group is a list of similar records.
    """
    # First pass: Group by (original_filename + date)
    filename_date_groups = defaultdict(list)
    
    for record in records:
        rec_id, orig_name, stored_name, transcript, status, source_path = record
        file_size = get_file_size(stored_name)
        
        if file_size is None:
            continue  # Skip missing files
        
        # Group by (original_filename, date) - ignore macOS metadata files
        if orig_name and not orig_name.startswith('._'):
            date = extract_date_from_stored_filename(stored_name)
            # Use tuple of (original_filename, date) as key
            key = (orig_name.upper(), date)
            filename_date_groups[key].append(record)
    
    # Separate filename+date duplicates from unique records
    duplicate_groups = []
    remaining_records = []
    
    for (filename, date), recs in filename_date_groups.items():
        if len(recs) > 1:
            duplicate_groups.append(recs)
            console.log(f"Found {len(recs)} duplicates with filename={filename}, date={date}")
        else:
            remaining_records.append(recs[0])
    
    console.log(f"Found {len(duplicate_groups)} filename+date-based duplicate groups")
    console.log(f"Remaining records to check for exact/similarity matching: {len(remaining_records)}")
    
    # Second pass: exact matches on remaining records
    exact_groups = defaultdict(list)
    similarity_candidates = []
    
    for record in remaining_records:
        rec_id, orig_name, stored_name, transcript, status, source_path = record
        file_size = get_file_size(stored_name)
        transcript_clean = transcript.strip() if transcript else ""
        
        if not transcript_clean:
            continue
        
        signature = (file_size, transcript_clean)
        exact_groups[signature].append(record)
    
    # Add exact duplicates to duplicate_groups
    for sig, recs in exact_groups.items():
        if len(recs) > 1:
            duplicate_groups.append(recs)
        else:
            similarity_candidates.append(recs[0])
    
    console.log(f"After exact matching: {len(duplicate_groups)} total groups, {len(similarity_candidates)} candidates for similarity")
    
    # Third pass: similarity matching on remaining candidates
    used_indices = set()
    
    for i in track(range(len(similarity_candidates)), description="Finding similar duplicates..."):
        if i in used_indices:
            continue
        
        rec1 = similarity_candidates[i]
        _, _, stored_name1, transcript1, _, _ = rec1
        size1 = get_file_size(stored_name1)
        transcript1_clean = transcript1.strip() if transcript1 else ""
        
        if not transcript1_clean:
            continue
        
        similar_group = [rec1]
        used_indices.add(i)
        
        for j in range(i + 1, len(similarity_candidates)):
            if j in used_indices:
                continue
            
            rec2 = similarity_candidates[j]
            _, _, stored_name2, transcript2, _, _ = rec2
            size2 = get_file_size(stored_name2)
            transcript2_clean = transcript2.strip() if transcript2 else ""
            
            if not transcript2_clean:
                continue
            
            # Check if similar
            if file_size_similar(size1, size2) and \
               text_similarity(transcript1_clean, transcript2_clean) >= TRANSCRIPT_SIMILARITY_THRESHOLD:
                similar_group.append(rec2)
                used_indices.add(j)
        
        if len(similar_group) > 1:
            duplicate_groups.append(similar_group)
    
    console.log(f"Found {len(duplicate_groups)} total duplicate groups (filename+date + exact + similar)")
    
    return duplicate_groups


def analyze_database(conn):
    """Analyze database for duplicates and trash."""
    cursor = conn.cursor()
    
    # Get all recordings
    cursor.execute("""
        SELECT id, original_filename, stored_filename, transcript, status, source_path
        FROM recordings
        ORDER BY id
    """)
    
    all_records = cursor.fetchall()
    console.log(f"Total records in database: {len(all_records)}")
    
    # Find missing files
    missing_files = []
    valid_records = []
    
    for record in all_records:
        rec_id, orig_name, stored_name, transcript, status, source_path = record
        file_size = get_file_size(stored_name)
        
        if file_size is None:
            missing_files.append(record)
        else:
            valid_records.append(record)
    
    console.log(f"Valid records (files exist): {len(valid_records)}")
    console.log(f"Missing files: {len(missing_files)}")
    
    # Find duplicate groups
    duplicate_groups = find_duplicate_groups(valid_records)
    
    return {
        'all_records': all_records,
        'duplicate_groups': duplicate_groups,
        'missing_files': missing_files,
    }


def display_analysis(analysis):
    """Display analysis results."""
    console.print("\n[bold cyan]Database Analysis Results[/bold cyan]\n")
    
    total_records = len(analysis['all_records'])
    duplicate_count = sum(len(group) - 1 for group in analysis['duplicate_groups'])
    unique_count = total_records - duplicate_count - len(analysis['missing_files'])
    
    console.print(f"Total records: [yellow]{total_records}[/yellow]")
    console.print(f"Unique files (after deduplication): [green]{unique_count}[/green]")
    console.print(f"Missing files: [red]{len(analysis['missing_files'])}[/red]")
    console.print(f"Duplicate groups: [yellow]{len(analysis['duplicate_groups'])}[/yellow]")
    console.print(f"Duplicate records to remove: [red]{duplicate_count}[/red]")
    
    total_to_remove = len(analysis['missing_files']) + duplicate_count
    final_count = total_records - total_to_remove
    
    console.print(f"\n[bold]After cleanup:[/bold]")
    console.print(f"  Records to remove: [red]{total_to_remove}[/red]")
    console.print(f"  Final count: [green]{final_count}[/green]")
    
    # Show some duplicate examples
    if analysis['duplicate_groups']:
        console.print(f"\n[bold]Duplicate Groups (showing first 10 of {len(analysis['duplicate_groups'])}):[/bold]")
        for i, group in enumerate(analysis['duplicate_groups'][:10]):
            # Calculate similarity info
            rec0 = group[0]
            _, orig_name0, stored_name0, transcript0, _, _ = rec0
            size0 = get_file_size(stored_name0)
            transcript0_clean = transcript0.strip() if transcript0 else ""
            
            # Check match type
            # 1. Check if all have same original filename AND date
            date0 = extract_date_from_stored_filename(stored_name0)
            all_same_filename_date = all(
                rec[1] and rec[1].upper() == orig_name0.upper() and
                extract_date_from_stored_filename(rec[2]) == date0
                for rec in group
            ) if orig_name0 and date0 else False
            
            # 2. Check if exact match (same size and transcript)
            is_exact = all(
                get_file_size(rec[2]) == size0 and 
                (rec[3].strip() if rec[3] else "") == transcript0_clean
                for rec in group
            )
            
            if all_same_filename_date:
                match_type = "FILENAME+DATE"
            elif is_exact:
                match_type = "EXACT"
            else:
                match_type = "SIMILAR"
            
            transcript_preview = transcript0_clean[:50] + "..." if len(transcript0_clean) > 50 else transcript0_clean
            
            table = Table(title=f"Group {i+1} [{match_type}]: Size≈{size0} bytes, '{transcript_preview}'")
            table.add_column("ID", style="cyan")
            table.add_column("Original Filename", style="yellow")
            table.add_column("Status", style="magenta")
            table.add_column("Similarity", style="white")
            table.add_column("Keep?", style="bold green")
            
            for j, rec in enumerate(group):
                rec_id, orig_name, stored_name, transcript, status, _ = rec
                
                # Calculate similarity to first record
                if j == 0:
                    similarity = "100%"
                else:
                    size_j = get_file_size(stored_name)
                    transcript_j = transcript.strip() if transcript else ""
                    sim = text_similarity(transcript0_clean, transcript_j)
                    similarity = f"{sim*100:.1f}%"
                
                keep = "✓" if j == 0 else "✗"
                table.add_row(str(rec_id), orig_name or "N/A", status or "N/A", similarity, keep)
            
            console.print(table)
    
    # Show missing files
    if analysis['missing_files']:
        console.print(f"\n[bold red]Missing Files (first 10 of {len(analysis['missing_files'])}):[/bold red]")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Original Filename", style="yellow")
        table.add_column("Stored Filename", style="red")
        
        for rec in analysis['missing_files'][:10]:
            rec_id, orig_name, stored_name, _, _, _ = rec
            table.add_row(str(rec_id), orig_name or "N/A", stored_name or "N/A")
        
        console.print(table)


def cleanup_database(conn, analysis, dry_run=True):
    """Remove duplicates and missing files from database."""
    cursor = conn.cursor()
    ids_to_delete = []
    
    # Collect IDs of missing files
    for rec in analysis['missing_files']:
        ids_to_delete.append(rec[0])
    
    # Collect IDs of duplicate records (keep first one in each group)
    for group in analysis['duplicate_groups']:
        # Keep the first record (lowest ID or EXPORTED status preferred)
        # Sort by: EXPORTED status first, then by ID
        sorted_group = sorted(group, key=lambda r: (r[4] != 'EXPORTED', r[0]))
        
        # Delete all except the first one
        for rec in sorted_group[1:]:
            ids_to_delete.append(rec[0])
    
    console.print(f"\n[bold]{'DRY RUN: Would delete' if dry_run else 'Deleting'} {len(ids_to_delete)} records...[/bold]")
    
    if not dry_run:
        if ids_to_delete:
            placeholders = ','.join('?' * len(ids_to_delete))
            cursor.execute(f"DELETE FROM recordings WHERE id IN ({placeholders})", ids_to_delete)
            conn.commit()
            console.print(f"[green]✓ Deleted {len(ids_to_delete)} records[/green]")
        else:
            console.print("[yellow]No records to delete[/yellow]")
    else:
        if len(ids_to_delete) <= 30:
            console.print(f"[yellow]IDs that would be deleted: {sorted(ids_to_delete)}[/yellow]")
        else:
            console.print(f"[yellow]IDs that would be deleted (first 30): {sorted(ids_to_delete)[:30]}...[/yellow]")
    
    return len(ids_to_delete)


def main():
    global TRANSCRIPT_SIMILARITY_THRESHOLD
    
    parser = argparse.ArgumentParser(description="Clean up microfoon database")
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be deleted without actually deleting (default)')
    parser.add_argument('--force', action='store_true',
                        help='Actually delete the records')
    parser.add_argument('--similarity', type=float, default=TRANSCRIPT_SIMILARITY_THRESHOLD,
                        help=f'Transcript similarity threshold (default: {TRANSCRIPT_SIMILARITY_THRESHOLD})')
    
    args = parser.parse_args()
    
    # Update threshold if provided
    TRANSCRIPT_SIMILARITY_THRESHOLD = args.similarity
    
    if not DB_PATH.exists():
        console.print(f"[red]Error: Database not found at {DB_PATH}[/red]")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Analyze
        analysis = analyze_database(conn)
        display_analysis(analysis)
        
        # Cleanup
        dry_run = not args.force
        deleted_count = cleanup_database(conn, analysis, dry_run=dry_run)
        
        if dry_run:
            console.print("\n[bold yellow]This was a DRY RUN. Use --force to actually delete records.[/bold yellow]")
        else:
            # Show final count
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM recordings")
            final_count = cursor.fetchone()[0]
            console.print(f"\n[bold green]✓ Cleanup complete! Final record count: {final_count}[/bold green]")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
