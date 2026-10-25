# Deploy MenuMate V3.2 to Render

## Files to upload to GitHub
Upload these files from this folder:
- app.py
- index.html
- README.md
- .gitignore
- render.yaml
- start.command (optional; only used locally)

Never upload an API key.

## Render
1. Create a new Web Service from the GitHub repository.
2. Language: Python 3
3. Build Command: leave blank if Render allows it; otherwise use:
   python3 -m pip install --upgrade pip
4. Start Command:
   python3 app.py
5. Plan: Free is sufficient for classroom testing if available.
6. Environment variable:
   OPENAI_API_KEY = your current valid API key
7. Deploy.

The app is configured to listen on 0.0.0.0 and Render's PORT environment variable.
