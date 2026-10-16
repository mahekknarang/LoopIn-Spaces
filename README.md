# LoopIn: Spaces

A small Flask venue planner for booking college rooms. It shows a weekly lecture timetable and date-specific reservations, accepts requests without user accounts, and lets an admin approve or reject requests. By default, data is stored in readable JSON files. For deployment, the app can use normalized Supabase tables through its REST API (no Supabase client package required).

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

The local demo admin PIN is **1234**. For a deployed service, set a private `ADMIN_PIN` environment variable in Render. Five incorrect attempts block that browser session for one minute.

The fresh project data contains the 14 venue definitions and an empty timetable and booking list. Venue rows contain a name, type, and capacity. Timetable rows contain venue, weekday, slot, and lecture. Booking rows contain a request ID, contact details, date, slots, status, and optional decision reason.

## College venues

The venue list is preloaded with LR1–LR6, LAB1–LAB5, BDA LAB, XICA AUDI, and XICA LIBRARY. Sample capacities are estimates; adjust them in the admin page to match your campus.

## Importing a timetable image

In Admin → Timetable, upload the original college timetable PDF or a clear image. The PDF importer reads the grid layout, Friday header, semester rows, course columns, and room codes; it recognizes LR1–LR6, LAB1–LAB5, BDA LAB, and XICA AUDI. It imports the Friday rows as the weekly Friday schedule and replaces the currently saved timetable, so review the result before use. The app's periods match the timetable: 07:45–08:40, 08:45–09:40, 09:45–10:40, 11:15–12:10, 12:15–01:10, 01:15–02:10, 02:45–03:40, 03:45–04:40, 04:45–05:40, and 05:45–06:40. Long breaks between 10:40–11:15 and 02:10–02:45 cannot be crossed by one booking. Image OCR remains available for simple images and loads Tesseract from jsDelivr, so the browser needs internet access. Check imported entries for mistakes.

## Supabase database

1. Create a Supabase project.
2. Open **SQL Editor** and run the contents of `supabase_schema.sql`.
3. In the Supabase project settings, copy the project URL and the server-side **Secret key** (not the Publishable key).
4. For local development, copy `.env.example` to `.env` and fill in the values. The app reads `.env` automatically; it is ignored by Git. For Render, add the same variables in **Dashboard → Environment**:
   - `SUPABASE_URL` — project URL
   - `SUPABASE_SERVICE_ROLE_KEY` — paste the Supabase **Secret key** (`sb_secret_…`), not the Publishable key. A legacy `service_role` key also works. Keep it server-side and out of GitHub
   - `LOOPIN_SECRET_KEY` — a long random value for Flask sessions
   - `ADMIN_PIN` — change the local demo PIN before sharing; set this in Render for the deployed admin PIN
5. After the SQL completes, start locally with `bash run.sh`, or redeploy Render. The app reads and writes separate `venues`, `timetable`, `bookings`, and `booking_slots` tables. The SQL copies any existing `spaces_store` data into those tables and leaves the old table in place as a backup. Once connected, an empty Supabase table remains empty; local demo JSON files are never copied over your database.

### What is stored

- `venues`: one row per space, with its type and capacity.
- `timetable`: one row per room, weekday, and period, with the class occupying it.
- `bookings`: one row per request, including requester/contact, purpose, room, date, status, and decision reason.
- `booking_slots`: one row per period requested, linked to its booking and removed automatically when that booking is deleted.

Row Level Security is enabled with no public access policies. The app uses the server-side Supabase key. The existing `spaces_store` backup table is not used by the new app.

Never add the service-role key to JavaScript, paste it into chat, or commit `.env` to the repository. Render's filesystem may reset between deploys, so Supabase is recommended for persistent bookings.

## Deploy manually on Render

Create a **Web Service** from the GitHub repository. Use the Python runtime, build command `pip install -r requirements.txt`, and start command `python app.py`. The app binds to Render’s `PORT` on `0.0.0.0` automatically. Set the Supabase environment variables above. The included `Procfile` has the same start command.

## DSA used and where

- **Hash map:** `dsa/hash_map_store.py` indexes venues, lectures, and request IDs for quick lookups.
- **Queue:** `dsa/queue_ds.py` is a linked first-in, first-out queue used to order pending requests.
- **Merge sort:** `dsa/sorting.py` sorts rooms by capacity, timetable slots, and request history.
- **Sliding window:** `dsa/sliding_window.py` finds consecutive open periods without crossing long campus breaks.
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
