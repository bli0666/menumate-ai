# MenuMate AI — V3.2 Render-ready

This build works both locally and on a public Render web service.

Important:
- Do not put `OPENAI_API_KEY` inside `app.py`, `index.html`, GitHub, or any public file.
- On Render, add it under Environment Variables.
- The app listens on `0.0.0.0` and uses Render's `PORT` automatically.

See `DEPLOY_RENDER.md` for deployment steps.

# MenuMate AI — V3.1 Live Prototype

## Important startup rule

**Do not double-click `index.html`.** That opens a page with no AI backend and causes `Failed to fetch`.

Run the app like this:

1. Unzip the folder.
2. Double-click `start.command`.
3. Paste your OpenAI API key when Terminal asks.
4. **Keep the Terminal window open.**
5. Use the browser page that opens automatically at `http://127.0.0.1:8000`.

## Upload rule

Upload the **actual menu JPG/PNG**. Do not upload a screenshot of Finder showing the menu filenames.

V3.1 also adds clearer diagnostics:
- detects when `index.html` was opened directly;
- detects when the local backend is disconnected;
- explains `Failed to fetch` instead of showing the raw browser error;
- keeps the two-step uploaded-menu-only analysis and appetizer/main/drink recommendation flow.

# MenuMate AI — V3 Live Prototype

V3 fixes two important issues:

1. **No sample-menu fallback.** The app now uses a two-step AI pipeline:
   - Step 1: transcribe only the items visible in the menu image you uploaded.
   - Step 2: create recommendations only from those extracted items.
   The backend also rejects recommendations whose original dish name was not present in the extracted uploaded menu.

2. **Direct meal recommendation after scanning.**
   The result screen now presents a recommended meal of up to 3–5 diverse items, organized when available as:
   - Appetizer
   - Main
   - Drink
   - optional Side
   - optional Dessert

   If a course is not present on the menu, the AI must not invent one.

The result page also shows:
- the exact menu image you uploaded;
- a collapsible “What AI actually read from your uploaded menu” section;
- risks and limitations.

## Run on Mac

1. Unzip the folder.
2. Double-click `start.command`.
3. Paste your OpenAI API key when Terminal asks.
4. The browser opens at `http://127.0.0.1:8000`.

If macOS blocks the command:

```bash
chmod +x start.command
./start.command
```

Manual start:

```bash
export OPENAI_API_KEY="your_api_key_here"
python3 app.py
```

## Allergy / health limitation

The prototype never guarantees that a dish is safe. A menu image cannot reliably reveal hidden sauces, recipe substitutions, shared fryers, utensils, or cross-contact. Severe allergies should always be confirmed directly with restaurant staff.
