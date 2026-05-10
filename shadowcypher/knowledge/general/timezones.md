# Timezones Reference

## UTC Offsets (Standard Time)

| Offset | Timezone Name | Example Cities |
|--------|--------------|----------------|
| UTC-12 | IDLW | Baker Island |
| UTC-11 | SST | American Samoa, Midway |
| UTC-10 | HST | Hawaii |
| UTC-9 | AKST | Alaska |
| UTC-8 | PST | Los Angeles, Seattle, Vancouver |
| UTC-7 | MST | Denver, Phoenix, Calgary |
| UTC-6 | CST | Chicago, Houston, Mexico City, Winnipeg |
| UTC-5 | EST | New York, Toronto, Miami, Lima, Bogota |
| UTC-4 | AST | Halifax, Puerto Rico, Caracas |
| UTC-3 | BRT | São Paulo, Buenos Aires, Montevideo |
| UTC-2 | GST (S.Georgia) | South Georgia |
| UTC-1 | AZOT | Azores |
| UTC+0 | GMT/UTC/WET | London (winter), Dublin, Lisbon, Reykjavik |
| UTC+1 | CET/WAT | Paris, Berlin, Rome, Lagos, Algiers |
| UTC+2 | EET/CAT | Cairo, Johannesburg, Helsinki, Athens |
| UTC+3 | MSK/EAT | Moscow, Istanbul, Nairobi, Riyadh |
| UTC+3:30 | IRST | Tehran |
| UTC+4 | GST | Dubai, Abu Dhabi, Baku |
| UTC+4:30 | AFT | Kabul |
| UTC+5 | PKT | Karachi, Islamabad |
| UTC+5:30 | IST | Mumbai, Delhi, Kolkata |
| UTC+5:45 | NPT | Kathmandu |
| UTC+6 | BST/BIOT | Dhaka, Almaty |
| UTC+6:30 | MMT | Yangon (Myanmar) |
| UTC+7 | ICT | Bangkok, Jakarta, Hanoi |
| UTC+8 | CST/AWST | Beijing, Shanghai, Singapore, Hong Kong, Perth |
| UTC+9 | JST/KST | Tokyo, Seoul, Pyongyang |
| UTC+9:30 | ACST | Adelaide, Darwin |
| UTC+10 | AEST | Sydney, Melbourne, Brisbane, Port Moresby |
| UTC+10:30 | LHST | Lord Howe Island |
| UTC+11 | SBT | Guadalcanal |
| UTC+12 | NZST/FJT | Auckland, Wellington, Fiji |
| UTC+13 | NZDT (DST) | Samoa, Tonga |
| UTC+14 | LINT | Kiribati (Line Islands) |

## Daylight Saving Time (DST)

DST shifts clock forward 1 hour in summer. Not all regions observe DST.

### DST Regions (Northern Hemisphere)
- USA/Canada: 2nd Sunday March → 1st Sunday November
  - PST (UTC-8) → PDT (UTC-7)
  - EST (UTC-5) → EDT (UTC-4)
- EU: Last Sunday March → Last Sunday October
  - CET (UTC+1) → CEST (UTC+2)
- UK: Last Sunday March → Last Sunday October
  - GMT (UTC+0) → BST (UTC+1)

### No DST
- Arizona, USA (except Navajo Nation)
- Hawaii, USA
- All of Africa
- China, Japan, South Korea, India
- Most of Southeast Asia
- Queensland, Western Australia (Australia)

## Major City Current Time Offsets

| City | Standard | With DST |
|------|---------|----------|
| New York | UTC-5 | UTC-4 (EDT) |
| Los Angeles | UTC-8 | UTC-7 (PDT) |
| Chicago | UTC-6 | UTC-5 (CDT) |
| London | UTC+0 | UTC+1 (BST) |
| Paris/Berlin | UTC+1 | UTC+2 (CEST) |
| Moscow | UTC+3 | No DST |
| Dubai | UTC+4 | No DST |
| Mumbai | UTC+5:30 | No DST |
| Singapore | UTC+8 | No DST |
| Beijing | UTC+8 | No DST |
| Tokyo | UTC+9 | No DST |
| Sydney | UTC+10 | UTC+11 (AEDT) |
| Auckland | UTC+12 | UTC+13 (NZDT) |

## Timezone Conversion

- To convert local time to UTC: subtract the UTC offset
- To convert UTC to local: add the UTC offset
- Example: New York is UTC-5; when NY is 3pm (15:00): UTC = 15 + 5 = 20:00 UTC

## Programming Notes

- Always store timestamps in UTC in databases
- Use ISO 8601 format: `2024-01-15T20:30:00Z` (Z = UTC)
- Never store local times; store UTC + user's timezone separately
- Python: `datetime.timezone.utc`, `pytz`, `zoneinfo` (Python 3.9+)
- JavaScript: `Date.toISOString()` returns UTC; `Intl.DateTimeFormat` for display

## IANA Timezone Database

Full list of timezone identifiers: `America/New_York`, `Europe/London`, `Asia/Tokyo`
Used in OS, programming languages, and most modern applications.
Online tool: https://www.timeanddate.com/worldclock/
