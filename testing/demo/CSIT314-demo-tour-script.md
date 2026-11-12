# CSIT314 full feature tour — voice-over script

Recording: `CSIT314-interior-design-tour.mp4` — 5 min 13 s, 1600x1000, no audio.
Read each line inside its window. At about 150 words a minute the windows fill
with room to breathe.

| Time | Role | On screen | Line to read |
|---|---|---|---|
| 0:00–0:09 | Designer | Sign-in, then the dashboard | Three roles, one system. The designer signs in first: Studio Verde, a residential studio. |
| 0:09–0:19 | Designer | Company profile, scrolled to the address and call fields | The company profile holds what a customer reads before they book: the service area, the meeting address and the video call room. One save and the public page follows. |
| 0:19–0:43 | Designer | Create Project; two photos added one by one; tag chips; tags field | A new project starts with a title, a description, a room and a style. Two photographs go into the queue and each one is analysed on upload. The analyser returns a palette and object tags; the tags appear as suggestions, never filled in. I click two, and Create Project stores it. |
| 0:43–0:57 | Designer | Edit form, description changed, Update Project, My Projects | The project opens on its own edit page. I change the description, press Update Project, and the card in My Projects shows the change. |
| 0:57–1:17 | Designer | Quote inbox, request opened, quote form | Quote inbox lists every request sent to this studio. This one carries a scope and a budget band. I answer with one total, S$42,000, valid for 21 days, plus a note on what the price covers. Nine per cent GST is added on top. |
| 1:17–1:30 | Customer | Sign out, sign in as Casey | Now the customer. |
| 1:30–1:47 | Customer | Request page with the quote, then the target form | The request shows the total, the GST line and the validity date. Not quite there: the customer names a target of S$38,000 with a reason. A target asks for a new price; it does not accept the old one. |
| 1:47–2:03 | Customer | Search filters, results, project page, save | Find a project. Room, style and a budget ceiling narrow the grid. Warm Minimal Living Room reads S$20,000 to S$40,000, and I save it to the shortlist. |
| 2:03–2:13 | Customer | Photo uploaded on the search page, tags, reranked list | A customer can also search with a photograph. The upload is analysed, the tags become filters, and the closest projects move up. |
| 2:13–2:20 | Customer | Saved list, Remove | Saved holds the shortlist. Remove takes the project out at once. |
| 2:20–2:42 | Customer | Designer page, booking form, confirmation | On the designer page I book a consultation: a video call, a free hour tomorrow, and a note. It stays pending until the designer accepts, and the meeting link stays hidden until then. |
| 2:42–3:05 | Customer | Project page, report form, confirmation | A project that looks wrong can be reported: a reason from the fixed list, a comment, and it goes to the platform staff. |
| 3:05–3:33 | Designer | Quote page with the counter, new version sent | Back as the designer: the counter sits under the quote. I send a new version at S$40,500, and the old quote stays in the history as superseded. |
| 3:33–3:40 | Designer | Consultations, Accept | The consultation is accepted from the same inbox. |
| 3:40–4:03 | Customer | Request page, Accept quote | The customer accepts the new total. That request closes; other open requests are left alone. |
| 4:03–4:10 | Customer | Appointments, link now visible | And now the meeting link appears, because the booking is accepted. |
| 4:10–4:36 | Admin | Report queue; both boxes ticked; Apply and close; row actioned | The administrator opens the report queue: the project, the designer, the reporter, the reason, and two independent controls. Take the project down, suspend the designer. Both, then Apply and close. The row moves to actioned. |
| 4:36–4:46 | Admin | Accounts filter Pending, Approve | A designer who registered waits in Pending. Approve, and the account becomes active. |
| 4:46–5:02 | Admin | Platform page, category added, weekly report | Platform management owns the categories every dropdown reads, so one add reaches every search at once, and the activity report counts accounts, projects and requests by day, week or month. |
| 5:02–5:13 | — | Sign-in page, "Account suspended" | Last, the suspended studio tries to sign in. Refused: the account is suspended. |

## Delivery notes

- About 780 words across 5 minutes, near 150 words a minute. If you run long,
  drop the second sentence of the company profile row first.
- The two sign-outs are silent by design (1:17 and 3:05). Do not fill them.
- At 0:57 the GST box is unticked, so the quote adds 9 per cent on top. Say
  "plus GST", not one all-in figure.
- At 4:10 the two checkboxes are separate on purpose: the admin can hide the
  project without punishing the designer, and the reverse.
- The closing line is the only proof of suspension on screen. Land it plainly.

## Re-recording

```bash
cd "C:/Users/Glenn Ang/Desktop/GITHUB REPOS/CSIT314-InteriorDesignWebsite"
DEMO_BASE=http://127.0.0.1:8010/api backend/.venv/Scripts/python.exe testing/demo/prepare_tour.py
python testing/demo/demo_tour.py --dry      # selector check, about 100 s
python testing/demo/demo_tour.py --speed 0.7
```

A take needs a fresh store: restart the backend, run `seed_all.py`, then
`prepare_tour.py`. Without the reset the quote is already accepted, the report
already exists and the booking is refused.

## Known limits of this take

- The accounts "Suspended" filter stalls on "Loading accounts" in this build, so
  the video proves the suspension with the refused sign-in instead of the list.
  That stall is a real frontend defect, not a recording artefact.
- The photo upload is one file per picker event. A two-file batch once lost both
  tiles when the second upload failed; the editor now keeps what succeeded.
