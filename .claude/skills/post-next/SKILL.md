---
name: post-next
description: Generate and post the next Carl Jung TikTok video. Finds the next unposted script, generates the video via caption-gen, researches SEO-optimized hashtags, posts to TikTok via upload-post.com, and updates the posting log.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebSearch, WebFetch
---

# /post-next — Post the Next Carl Jung TikTok Video

You are automating the TikTok posting pipeline for the Carl Jung psychology channel (@heal.with.jung).

## Working Directory

All paths are relative to: `/home/silviu/coding/carl_jung/caption-gen/`

## Step 1: Find the Next Unposted Script

1. Read `posting_log.json` in the project root. If it doesn't exist, create it with `[]`.
2. The log is a JSON array of objects with `script_number`, `filename`, `date_posted`, `status`, `characters_used`, and `cost_usd` fields.
3. List all `.txt` files in `scripts/` matching the pattern `NNN-*.txt` (e.g., `001-the-mask-you-built.txt`).
4. Extract the number from each filename (the first 3 digits).
5. Find the **lowest-numbered script** whose number is NOT in the log (regardless of status).
6. If ALL scripts have been posted, report: "All 93 scripts have been posted." and stop.
7. Announce: "Next script: NNN-slug-name"

## Step 2: Generate the Video (If Needed)

1. Check if `output/<script-filename-without-txt>.mp4` already exists.
2. **If the video exists**: Skip generation. Report: "Video already exists, skipping generation."
3. **If the video does NOT exist**: Generate it:
   ```bash
   cd /home/silviu/coding/carl_jung/caption-gen && python3 caption_gen.py --script scripts/<filename>.txt
   ```
   The script auto-loads API keys from `.env` and uses defaults (Theo Silk voice, emerging image).
4. **On failure**: Retry ONCE. If it fails again, report the error and STOP. Do NOT update the log.
5. Note the character count from the output (line: "ElevenLabs cost: N characters") and the estimated cost (line: "Estimated cost: $X.XXXX").

## Step 3: SEO Research for Caption and Hashtags

1. Read the script file to understand the topic and core Jungian concept.
2. Identify the main theme (e.g., Shadow work, Anima/Animus, Individuation, Inner Child, Projection, etc.).
3. Perform **2 WebSearches**:
   - Search: `TikTok trending hashtags [main theme] psychology self-help 2026`
   - Search: `TikTok [specific Jungian concept] viral content psychology`
4. From the results, select the **2 best custom hashtags** that:
   - Are currently trending or have high engagement
   - Match this specific script's topic
   - Are NOT too broad (#fyp, #viral) or too narrow
5. The 3 fixed hashtags are always: `#CarlJung #Psychology #ShadowWork`
6. Total: 5 hashtags per post (3 fixed + 2 custom)

## Step 4: Craft the TikTok Caption

Create an SEO-optimized caption following this formula:
1. **Hook line** (the most compelling insight from the script — 1 sentence that stops the scroll)
2. **Context line** (1 sentence expanding the insight with an SEO keyword woven in naturally)
3. **Hashtags** (the 5 hashtags on a new line or appended)

**Rules:**
- Total caption: 150-300 characters (excluding hashtags)
- Use the script's actual language — pull the best line, don't rewrite it
- Weave in 1-2 SEO keywords naturally (e.g., "healing", "self-discovery", "inner work", "unconscious mind")
- Tone: wise, calm, intriguing — match the channel's voice
- Do NOT use exclamation marks
- Do NOT use emoji

**Example caption:**
```
The shadow you refuse to face will run your life from the darkness. Carl Jung understood that wholeness begins where your fear ends. #CarlJung #Psychology #ShadowWork #InnerChild #HealingJourney
```

## Step 5: Post to TikTok via Upload-Post.com

Post the video using the upload-post Python SDK:

```bash
cd /home/silviu/coding/carl_jung/caption-gen && python3 -c "
from dotenv import load_dotenv
import os
load_dotenv('.env')
from upload_post import UploadPostClient
client = UploadPostClient(api_key=os.environ['UPLOAD_POST_API_KEY'])
result = client.upload(
    file_path='output/SCRIPT_NAME.mp4',
    title='''CAPTION_TEXT_HERE''',
    platforms=['tiktok'],
    profile=os.environ['UPLOAD_POST_PROFILE']
)
print(result)
"
```

Replace `SCRIPT_NAME` and `CAPTION_TEXT_HERE` with actual values.

**On failure**: Retry ONCE. If it fails again, report the error and STOP. Do NOT update the log.

## Step 6: Update the Posting Log

Read `posting_log.json`, append a new entry, and write it back:

```json
{
  "script_number": 3,
  "filename": "003-the-child-still-waiting",
  "date_posted": "2026-04-01T14:30:00",
  "status": "success",
  "characters_used": 847,
  "cost_usd": 0.1677
}
```

- `script_number`: the integer from the filename
- `filename`: the script filename without `.txt`
- `date_posted`: current ISO 8601 timestamp
- `status`: "success" or "failed"
- `characters_used`: the ElevenLabs character count (0 if video was pre-existing)
- `cost_usd`: the estimated generation cost in USD from the "Estimated cost" output line (0 if video was pre-existing). Calculated as `characters_used * ELEVENLABS_COST_PER_CHAR` (env var, defaults to $0.000198/char ≈ ElevenLabs Pro plan rate).

## Step 7: Report Summary

Output a clear summary:

```
--- Post Complete ---
Script: 003-the-child-still-waiting
Caption: [the full caption with hashtags]
ElevenLabs cost: 847 characters ($0.1677)
Status: Success
Remaining: 90 scripts
```

Include the number of remaining unposted scripts.
