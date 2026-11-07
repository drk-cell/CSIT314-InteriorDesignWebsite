# Data files for the large test run

Fill these four files, then send them back. They are plain CSV: they open in
Excel, Google Sheets or Notepad. Save them as **CSV (comma delimited)** and keep
the file names exactly as they are.

| File | One row means | Order matters |
|---|---|---|
| `accounts.csv` | one login | first |
| `companies.csv` | one designer company | second, after accounts |
| `projects.csv` | one portfolio project | third, after companies |
| `quote_requests.csv` | one customer asking a company for a price | fourth |

The order matters because a project needs its designer to exist first, and a
request needs both the customer and the company.

## Rules that apply to every file

- Keep the header row. Change only the rows under it.
- One row per record. Do not merge cells.
- A row that starts with `#` is ignored, so you can leave notes.
- Blank rows are ignored.
- Extra spaces around a value are removed.
- Money is in **Singapore dollars**, for example `25000` or `25,000.00`. Do not
  write cents, `$` or `S$`.
- A list uses a **semicolon**, not a comma, because the comma separates columns:
  `photo-01.jpg;photo-02.jpg`.
- Delete the example rows before you send the file back.

## accounts.csv

| Column | Required | Rule |
|---|---|---|
| `email` | yes | unique in the file, looks like `name@example.com` |
| `display_name` | yes | 1 to 80 characters |
| `role` | yes | `CUSTOMER` or `DESIGNER`, in capitals |
| `password` | no | defaults to `passw0rd123` |

```
email,display_name,role,password
nadia@example.com,Nadia Rahman,CUSTOMER,passw0rd123
lin@example.com,Lin Wei,DESIGNER,passw0rd123
```

## companies.csv

| Column | Required | Rule |
|---|---|---|
| `designer_email` | yes | must match a `DESIGNER` in `accounts.csv`, or a designer already on the platform |
| `name` | yes | the company name, 1 to 120 characters, unique |
| `description` | no | up to 1000 characters |
| `contact_email` | yes | an address customers can write to |
| `contact_phone` | no | free text |
| `location` | no | city, for example `Singapore` |
| `logo_url` | no | a web address to an image |

```
designer_email,name,description,contact_email,contact_phone,location,logo_url
lin@example.com,Studio Lin,Warm residential work,hello@studiolin.sg,+65 6123 4567,Singapore,
```

## projects.csv

| Column | Required | Rule |
|---|---|---|
| `designer_email` | yes | the designer who owns the project |
| `title` | yes | 1 to 120 characters |
| `category` | yes | must be one of the rooms the platform lists, see below |
| `style` | yes | must be one of the styles the platform lists, see below |
| `budget_min` | yes | dollars, not above `budget_max` |
| `budget_max` | yes | dollars |
| `description` | no | up to 2000 characters |
| `status` | no | `CURRENT` or `PAST`, defaults to `CURRENT` |
| `images` | no | up to 8 photo addresses, separated by `;` |
| `tags` | no | up to 12 tags, separated by `;` |

Rooms: `Balcony`, `Bathroom`, `Bedroom`, `Children's Room`, `Dining Room`,
`Home Office`, `Kitchen`, `Living Room`, `Studio`, `Whole Home`.

Styles: `Minimal`, `Scandinavian`, `Contemporary`, `Traditional`, `Japandi`,
`Industrial`, `Eclectic`.

For photos, use the ones already in the project, so no upload is needed:
`/portfolio/photos/photo-01.jpg` up to `/portfolio/photos/photo-16.jpg`.

```
designer_email,title,category,style,budget_min,budget_max,description,status,images,tags
lin@example.com,Compact Kitchen,Kitchen,Minimal,18000,32000,Reworked for one cook,CURRENT,/portfolio/photos/photo-07.jpg;warm palette;oak
```

## quote_requests.csv

| Column | Required | Rule |
|---|---|---|
| `customer_email` | yes | must match a `CUSTOMER` in `accounts.csv` |
| `company_name` | yes | must match a `name` in `companies.csv` |
| `title` | yes | 1 to 120 characters |
| `scope` | yes | what the work involves, up to 2000 characters |
| `budget_min` | yes | dollars |
| `budget_max` | yes | dollars, not below `budget_min` |
| `target` | no | the price the customer wants, in dollars |
| `answer_total` | no | if filled, the designer answers at once, in dollars |
| `answer_days` | no | how long the answer stays valid, 1 to 90, defaults to 14 |
| `gst_included` | no | `YES` or `NO`, defaults to `NO` |

A customer may hold only **one open request per company**. The importer reports
the second one as a rejected row instead of creating it.

```
customer_email,company_name,title,scope,budget_min,budget_max,target,answer_total,answer_days,gst_included
nadia@example.com,Studio Lin,Kitchen quote,Repaint and new cabinets,20000,40000,35000,36000,14,NO
```

---

# What the platform stores

A project row becomes a record like this. You do not type this yourself; it is
here so you can see what your CSV produces.

```json
{
  "id": "6f1c0a52-8a90-4d20-9d47-2f0c6a4b9e11",
  "owner_id": "0b2c7a44-1f36-4a1b-9d92-5f0a3c8e7d21",
  "company_id": "3d9e5b10-7c42-4f68-8a11-0c2b6d4e9f30",
  "title": "Compact Kitchen",
  "description": "Reworked for one cook",
  "style": "Minimal",
  "category": "Kitchen",
  "budget_min": 1800000,
  "budget_max": 3200000,
  "status": "CURRENT",
  "images": ["/portfolio/photos/photo-07.jpg"],
  "tags": ["warm palette", "oak"],
  "view_count": 0,
  "shortlist_count": 0,
  "created_at": "2026-11-07T10:15:00+00:00",
  "updated_at": "2026-11-07T10:15:00+00:00"
}
```

Two things to notice:

1. Money is stored in **cents**. Your `18000` dollars becomes `1800000`.
2. The room, the style and the tags are the only things a customer can search.
   If a row has no tags, that project is harder to find.

# Checking your file before you send it

You can check it yourself. The app must be running.

1. Put the four CSV files in this folder.
2. Double-click `6-load-my-data.bat` in the top folder.
3. Read the summary. It prints how many rows were accepted and how many were
   rejected, with the line number and the reason for each rejection.

A good file ends with:

```
accounts.csv            12 accepted    0 skipped    0 rejected
companies.csv            4 accepted    0 skipped    0 rejected
projects.csv            30 accepted    0 skipped    0 rejected
quote_requests.csv      18 accepted    0 skipped    0 rejected

Every row was accepted.
```

If any row is rejected, the report names the line and the reason:

```
Rejected rows:
  projects.csv line 5: budget_min is above budget_max
  projects.csv line 9: style 'Steampunk' is not in the list: Minimal, Scandinavian, ...
  quote_requests.csv line 4: the row has more values than the header; a comma inside a field needs double quotes
```

Fix the file and run the launcher again. Rows already imported are counted as
**skipped**, so a second run never duplicates anything.
