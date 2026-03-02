# User Guide — Voice & Vision Assistant

**Version**: 1.0.0 | **For**: Blind and Low-Vision Users

This guide tells you how to use the Voice & Vision Assistant. It explains all voice commands,
features, and settings in plain language.

---

## Getting Started

### What You Need

- A computer or device with a microphone and camera
- Python 3.10 or newer (your helper may set this up for you)
- Internet access
- API keys for LiveKit, Deepgram, and ElevenLabs (your administrator provides these)

### Starting the Assistant

1. Open a terminal or command prompt.
2. Type this command and press Enter:

```
python -m apps.realtime.entrypoint start
```

3. You will hear a welcome message when the assistant is ready.
4. Start speaking after you hear the tone.

### Stopping the Assistant

Press **Ctrl + C** in the terminal, or say **"stop assistant"**.

---

## Voice Commands

Speak naturally. The assistant understands complete sentences. Here are common commands.

### Seeing Your Surroundings

| Say | What Happens |
|-----|-------------|
| "What do you see?" | The assistant describes everything in front of the camera |
| "Describe the scene" | Detailed description of your surroundings |
| "Are there any people here?" | Tells you if people are present |
| "What is in front of me?" | Describes objects directly ahead |
| "Read the text in the image" | Reads any text the camera can see |

### Finding Obstacles

| Say | What Happens |
|-----|-------------|
| "Are there any obstacles?" | Lists nearby objects and their distance |
| "Is the path clear?" | Tells you if the way ahead is safe |
| "What is close to me?" | Lists objects within 2 metres |

The assistant will also speak automatically if something is very close (under 1 metre).

### Reading Text

| Say | What Happens |
|-----|-------------|
| "Read this text" | Reads text visible to the camera |
| "What does this sign say?" | Reads a sign or label |
| "Scan this QR code" | Reads a QR code and explains its contents |
| "Read this braille" | Reads braille text from the camera |

### Searching the Internet

| Say | What Happens |
|-----|-------------|
| "Search for [topic]" | Searches the internet and reads results |
| "What is the weather today?" | Finds current weather |
| "Tell me about [subject]" | Looks up information on any topic |

### Memory (Optional Feature)

Memory is turned off by default to protect your privacy.
Your administrator must turn it on if you want to use it.

| Say | What Happens |
|-----|-------------|
| "Remember that [information]" | Saves something for later |
| "What did I tell you about [topic]?" | Recalls saved information |
| "Forget everything" | Deletes all saved memories |

### General Conversation

| Say | What Happens |
|-----|-------------|
| "Hello" | The assistant greets you |
| "Help" | Lists available commands |
| "What can you do?" | Lists all features |
| "Repeat that" | Repeats the last response |

---

## Features

### Obstacle Detection

The assistant watches through the camera and warns you about nearby objects.

- **Critical warning** (under 1 metre): "Stop! Chair very close ahead."
- **Near warning** (1 to 2 metres): "Caution, table 1.5 metres slightly left."
- **Far warning** (2 to 5 metres): "Door 3 metres ahead."

You can turn obstacle detection on or off in the configuration file.

### QR Code Scanning

Point the camera at any QR code and say "scan this QR code."
The assistant reads the code and explains what it means.

Examples of what QR codes can do:
- Open a website and read the page title
- Tell you about a bus stop and routes
- Share contact details
- Connect to a Wi-Fi network (reads the name only)

### Braille Reading

Point the camera at braille text (on a sign, label, or page) and say "read this braille."
The assistant converts the braille dots to text and speaks it aloud.

### Virtual Avatar (Optional)

If your administrator has set up the Tavus avatar, you will have a visual face
in video calls. This helps sighted people in meetings see you clearly.
The avatar speaks using the same voice as the assistant.

---

## Configuration

Settings are stored in the `.env` file in the application folder.
Ask your administrator to change settings. Common settings are:

| Setting | What It Does | Default |
|---------|-------------|---------|
| `SPATIAL_PERCEPTION_ENABLED` | Turn obstacle detection on/off | true |
| `ENABLE_QR_SCANNING` | Turn QR code scanning on/off | true |
| `MEMORY_ENABLED` | Turn memory/recall on/off | false |
| `ENABLE_AVATAR` | Turn virtual avatar on/off | false |
| `LOG_LEVEL` | How much detail is logged | INFO |

---

## Troubleshooting

### The assistant does not respond to my voice

1. Check that your microphone is plugged in and not muted.
2. Check that your Deepgram API key is set correctly.
3. Speak clearly and wait for the tone before speaking.
4. Try restarting the assistant.

### The camera description seems wrong

1. Make sure the camera is pointed at what you want described.
2. Check that the camera is not covered.
3. Make sure there is enough light in the room.
4. Ask again — say "Describe the scene" or "What do you see?"

### QR code scanning does not work

1. Hold the QR code steady in front of the camera.
2. Make sure the QR code takes up about a quarter of the camera view.
3. Ensure good lighting — avoid glare on shiny surfaces.
4. The QR code must have clear edges and good contrast.

### The voice sounds wrong or stops mid-sentence

1. Check your internet connection.
2. Check that your ElevenLabs API key is valid.
3. Restart the assistant.

### I hear "feature not available"

Some features need optional software to be installed.
Ask your administrator to run:

```
pip install -r requirements-extras.txt
```

---

## Privacy

- The camera is only active while the assistant is running.
- No video is stored or sent to external services.
- Memory is turned off by default — nothing is saved without your consent.
- Face recognition, if enabled, only saves face data after you give permission.
- You can delete all saved data by saying "forget everything."

---

## Getting Help

- Say **"help"** at any time for a list of commands.
- Contact your administrator for setup or API key issues.
- For bugs or feedback: <muhammedaslam179@gmail.com>
