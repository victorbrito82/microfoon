We want to make an app that I have an application that when a USB is plugged in to your computer it reads the audio files rename them, transcribe them, and put them in specific directories and summarize system with AI. 

1. user plugs in usb
2. system recognizes usb stick and starts the program
3. program shows there are new audio files
4. program asks user to start transcribing
5. program 
    - loads audiofiles
    - saves audiofiles in a configurable directory and gives the file a name with timestamp
    - program transcribes the file and stores the transcribed text with timestamp in a database;
    - program summarizes the transcribed text and stores the summarized text with timestamp in a database;
    - program derives a title from the summarized text and stores it in a database;
    - title, summary, original transcribes text and the location of the audit file are all linked and croo referenced;
    - program shows results of transcribed files and askes the user if he is ok to delete the files from the usb stick and to compress the original audio files to a low quality mp3 file; (opus file). App asks user if he wants to synchronize to Obsidian.
6.User can export the database to obsidian or other note taking app.
7. make separate prompts that can easility be editied from a env file;
in the env file store the api key of the llm;

8. use sql lite. The llm needs to be able to recognize languge and to know dutch and english.