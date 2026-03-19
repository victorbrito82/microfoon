here are possible future improvements of this project:

1. My new microphone is now correctly adding date to the files, so I can use these dates to update filenames.
2. check the folder structure for unnecessary files and remove them.
3. clean up this project file structure.
4. The microphone can change name: first it was "VOICE", now it is "RECORD". the user should be able to change the name of the microphone without the code not working anymore. (Note: this is already supported by changing TARGET_VOLUME_NAME in the .env file)   
5. Compression is failing
    Compressing recordings/20260319_103642_REC031.WAV to         audio.py:40
           recordings/20260319_103642_REC031.compressed.mp3...                     
           Compression failed: Decoding failed. ffmpeg returned error   audio.py:47
           code: 8                                                                 
                                                                                   
           Output from ffmpeg/avlib:                                               
                                                                                   
           ffmpeg version 8.0.1 Copyright (c) 2000-2025 the FFmpeg                 
           developers                                                              
             built with Apple clang version 17.0.0 (clang-1700.6.3.2)              
             configuration:                                                        
           --prefix=/opt/homebrew/Cellar/ffmpeg/8.0.1_3 --enable-shared            
           --enable-pthreads --enable-version3 --cc=clang                          
           --host-cflags= --host-ldflags= --enable-ffplay --enable-gpl             
           --enable-libsvtav1 --enable-libopus --enable-libx264                    
           --enable-libmp3lame --enable-libdav1d --enable-libvpx                   
           --enable-libx265 --enable-openssl --enable-videotoolbox                 
           --enable-audiotoolbox --enable-neon                                     
             libavutil      60.  8.100 / 60.  8.100                                
             libavcodec     62. 11.100 / 62. 11.100                                
             libavformat    62.  3.100 / 62.  3.100                                
             libavdevice    62.  1.100 / 62.  1.100                                
             libavfilter    11.  4.100 / 11.  4.100                                
             libswscale      9.  1.100 /  9.  1.100                                
             libswresample   6.  1.100 /  6.  1.100                                
            Guessed Channel Layout: stereo                                         
           Input #0, wav, from 'recordings/20260319_103642_REC031.WAV':            
             Duration: 00:28:12.93, bitrate: 192 kb/s                              
             Stream #0:0: Audio: adpcm_ima_wav ([17][0][0][0] /                    
           0x0011), 24000 Hz, stereo, s16p, 192 kb/s                               
            Unknown encoder 'pcm_s4le'                                             
            Error selecting an encoder                                             
           Error opening output file -.                                            
           Error opening output files: Encoder not found                           
                                                                                   
