# CSIT314 demo — voice-over script

Recording: `CSIT314-interior-design-demo.mp4` — 2 min 01 s, 1600x1000, no audio.
Read each line inside its window. The windows do not overlap, so a calm pace
works; do not rush the two logins.

| Time | Role | On screen | Line to read |
|---|---|---|---|
| 0:00–0:07 | Designer | Sign-in page, then the dashboard | Three roles, six use cases. We start as the designer, signing in to Studio Verde. |
| 0:07–0:19 | Designer | Quote inbox, then one request (use case 1) | This is the quote inbox: every renovation request a customer has sent to the studio. The table shows the title, the budget band, the state and the date. Opening it shows the scope the designer has to price. |
| 0:19–0:32 | Designer | My Projects, Edit, Update Project (use case 4) | My Projects is the portfolio. I open a project, update its details, and press Update Project. The change is saved, and the card now shows the refreshed title. |
| 0:32–0:39 | — | Sign out, customer sign-in | Now the customer. |
| 0:39–0:55 | Customer | Search filters, results, project page, save (use case 2) | Find a project. I choose a category, a style and a budget ceiling, and the catalogue narrows to work that matches. I open Warm Minimal Living Room to read its photos, budget and tags, then save it to my shortlist. |
| 0:55–1:02 | Customer | Saved list, Remove (use case 3) | Saved lists the favourites. I remove this project, and it leaves the list immediately. |
| 1:02–1:22 | Customer | Designer page, booking form, confirmation (use case 5) | On the designer's page I book a consultation. I choose a video call, a free hour tomorrow, and add a note. The confirmation shows the day, the time, and explains that the meeting link appears once the designer accepts. |
| 1:22–1:44 | Customer | Project page, report form, confirmation (use case 6) | Back in the catalogue, if a project breaks the rules I open Report this project, choose a reason, add a comment, and send. The report goes straight to the administrator. |
| 1:44–2:01 | Admin | Admin page, Reported projects queue | Signed in as the administrator, the report queue shows the project, the designer, the reporter and the reason. From here staff can take the project down, suspend the designer, or dismiss the report. |

## Delivery notes

- About 200 words in 2 minutes, so roughly 140 words a minute. Leave the rest as
  pauses; the screen needs the silence more than the script does.
- Do not talk over the two sign-ins (0:00 and 0:32). Type sounds are the only
  sound in the take.
- The confirmation at 1:02 is the point of use case 5: say "the meeting link
  appears once the designer accepts" while it is on screen.
- At 1:44 the queue holds two reports: the one just filed (Soft Neutral
  Bedroom) and the seeded one (Curated Living Room). The line covers both.

## Re-recording

```bash
cd "C:/Users/Glenn Ang/Desktop/GITHUB REPOS/CSIT314-InteriorDesignWebsite"
DEMO_BASE=http://127.0.0.1:8010/api backend/.venv/Scripts/python.exe testing/demo/prepare_demo.py
python testing/demo/demo_drive.py --dry     # selector check, about 40 s
python testing/demo/demo_drive.py --speed 0.8
```

A take needs a fresh store: restart the backend, run `seed_all.py`, then
`prepare_demo.py`. Otherwise the booking is refused (one open per company) and
the report is refused (one open per project).
