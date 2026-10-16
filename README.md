# LoopIn: Spaces

A small Flask venue planner for booking college rooms. It shows a weekly lecture timetable and date-specific reservations, accepts requests without user accounts, and lets an admin approve or reject requests. By default, data is stored in readable JSON files. For deployment, the app can use Supabase through its REST API (no Supabase client package required).

## Start on Mac

From Terminal, go to this project folder, then run:

```bash
bash run.sh
```

Or run each step yourself:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open the exact URL printed in the terminal. The app tries port 5000 first and automatically uses port 5001 if 5000 is busy (often because of AirPlay Receiver).

## Start on Windows

Double-click `run.bat`, or open Command Prompt in the project folder and run:

```bat
py -3 --version
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open the URL printed in the terminal. If port 5000 is occupied, the app uses 5001 automatically.

## Admin and data

The default admin PIN is **1234**. Change `ADMIN_PIN` in `config.py` before sharing the project. Five incorrect attempts block that browser session for one minute.

The fresh project data contains the 14 venue definitions and an empty timetable and booking list. Venue rows contain a name, type, and capacity. Timetable rows contain venue, weekday, slot, and lecture. Booking rows contain a request ID, contact details, date, slots, status, and optional decision reason.

## College venues

The venue list is preloaded with LR1–LR6, LAB1–LAB5, BDA LAB, XICA AUDI, and XICA LIBRARY. Sample capacities are estimates; adjust them in the admin page to match your campus.

## Importing a timetable image

In Admin → Timetable, upload a clear image. Browser OCR automatically imports rows that contain the venue, weekday, time slot, and class name together (for example: `LR1 Monday 9-10 DSA`). The import replaces the current weekly timetable after it finds valid entries. If the image layout is too complex or recognition fails, the existing timetable is kept; use a clearer image or edit entries manually. OCR loads from jsDelivr, so the browser needs internet access. Check imported entries for OCR mistakes.

## Supabase database

1. Create a Supabase project.
2. Open **SQL Editor** and run the contents of `supabase_schema.sql`.
3. In the Supabase project settings, copy the project URL and the **service_role** key.
4. For local development, copy `.env.example` to `.env` and fill in the values. The app reads `.env` automatically; it is ignored by Git. For Render, add the same variables in **Dashboard → Environment**:
   - `SUPABASE_URL` — project URL
   - `SUPABASE_SERVICE_ROLE_KEY` — service-role secret; keep it server-side and out of GitHub
   - `LOOPIN_SECRET_KEY` — a long random value for Flask sessions
5. Start locally with `bash run.sh`, or redeploy Render. When both Supabase variables are present, venue, timetable, and booking data use the `spaces_store` table. On first connection, the current local JSON files seed any missing Supabase rows. Here the timetable and bookings are empty so your new database starts fresh; the 14 venue definitions are retained.

Never add the service-role key to JavaScript, paste it into chat, or commit `.env` to the repository. Render's filesystem may reset between deploys, so Supabase is recommended for persistent bookings.

## Deploy manually on Render

Create a **Web Service** from the GitHub repository. Use the Python runtime, build command `pip install -r requirements.txt`, and start command `python app.py`. The app binds to Render’s `PORT` on `0.0.0.0` automatically. Set the Supabase environment variables above. The included `Procfile` has the same start command.

## DSA used and where

- **Hash map:** `dsa/hash_map_store.py` indexes venues, lectures, and request IDs for quick lookups.
- **Queue:** `dsa/queue_ds.py` is a linked first-in, first-out queue used to order pending requests.
- **Merge sort:** `dsa/sorting.py` sorts rooms by capacity, timetable slots, and request history.
- **Sliding window:** `dsa/sliding_window.py` finds consecutive open slots without crossing the lunch break.
- **Greedy best fit:** `dsa/greedy_best_fit.py` chooses the smallest room that fits the requested group.
- **Trie:** `dsa/trie.py` finds room names by their typed prefix on the booking screen.

Run tests with:

```bash
python -m unittest discover -s tests -v
```

## Troubleshooting

- **Python not found:** install Python 3.9 or newer from python.org. On Mac, use `python3`; on Windows, try `py -3`.
- **pip install fails:** activate `.venv`, check that your internet connection is available, then run `python -m pip install -r requirements.txt` again.
- **Page shows an error:** keep the terminal open while the app runs, use the exact printed URL, and use the Retry button on the booking page.
- **Admin PIN not working:** the default is `1234`; check `ADMIN_PIN` in `config.py`. Five wrong attempts block the session for one minute.

## Future improvements

1. Add proper admin accounts and password hashing.
2. Send email notifications when a request gets a decision.
3. Support recurring bookings and special schedules.
4. Add a calendar view with export support.
5. Add room-demand analytics.
