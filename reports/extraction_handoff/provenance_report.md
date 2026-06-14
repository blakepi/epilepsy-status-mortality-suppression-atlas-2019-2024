# Provenance Report

- CDC WONDER database name: Current Final Multiple Cause of Death Data, 2018-2024, Single Race
- Assumed database ID: `D157`
- Request URL: https://wonder.cdc.gov/mcd-icd10-expanded.html
- Script version: `0.1.0`

## Cause Syntax Provenance

- MCD G40/G41 queries used Finder-style two-line text in `#TD157\.V13-AND1`.
- Q010 used the same MCD AND1 text and `U07.1 (COVID-19)` in `#TD157\.V13-AND2`.
- Q011/Q012/Q014 used Finder-style two-line G40/G41 text in UCD `#TD157\.V2`; MCD fields remained blank/default.
- Literal `G40-G41` was not used for validated exports.

## Exports

### Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed

- Query ID: `Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.xls`
- Processed CSV: `data\processed\csv\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.csv`
- Processed parquet: `data\processed\parquet\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.parquet`
- Request XML path if available: `data\raw\xml_requests\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.xml`
- Raw SHA256: `ab7484e79e0fd626d8af053d1adc4f9d2e50bab5ed260a45bb2067e17cba9cf5`
- Processed CSV SHA256: `4c00949ba5dd954d47698f03087886d32be976fa94ad2b666e1b122fe39aeb41`
- Processed parquet SHA256: `232a11e4401c7e130360d7dde9de98f2f6f5d4ac63f9888c30691c3309c5c5ba`
- Notes/caveats path: `data\processed\csv\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed

- Query ID: `Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.xls`
- Processed CSV: `data\processed\csv\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.csv`
- Processed parquet: `data\processed\parquet\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.parquet`
- Request XML path if available: `data\raw\xml_requests\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.xml`
- Raw SHA256: `4e4d694f0ec02d1d93a30b94c95706c7890c41e532ddcb75f1bc00310eea956d`
- Processed CSV SHA256: `cb67504a26b04e1569fb89369fbf0d7dd7c2ce8ad89038c8ef7c935bf5506576`
- Processed parquet SHA256: `82ea4bfd39c6b80a9e9a40ab9017399bdc5b8f24f71a7c37a41f0efdc797697f`
- Notes/caveats path: `data\processed\csv\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q003_national_year_mc_g40_g41_2019_2024

- Query ID: `Q003_national_year_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q003_national_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q003_national_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q003_national_year_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q003_national_year_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `d34b96e103bfe3348f0b256ac581116cfab6b0afc1d8cd4fe63c83ae8c68159a`
- Processed CSV SHA256: `2e941c2c4d784e96c859b3cf251223196d3734bd25fe7bc56608ccb743536b05`
- Processed parquet SHA256: `9834a67f53bb56f66ee189de1a11fa02ecde51294efebb50f141c13c3fb9d64e`
- Notes/caveats path: `data\processed\csv\Q003_national_year_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q004_state_year_mc_g40_g41_2019_2024

- Query ID: `Q004_state_year_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q004_state_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q004_state_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q004_state_year_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q004_state_year_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `0958a1a265993b5b7d036fcb976d9d29d5210bb77ba0873e9ccdd6c2bae003fd`
- Processed CSV SHA256: `d01a14b0363dd0c1e2b5a3c16d823930d3d26c8bc6eca3761f71145b4e9cdd13`
- Processed parquet SHA256: `51fd7a24dc23271bb1e039a4646f8d6edf83bec035c21c6eac5873113d634ec5`
- Notes/caveats path: `data\processed\csv\Q004_state_year_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q005_urbanization_year_mc_g40_g41_2019_2024

- Query ID: `Q005_urbanization_year_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q005_urbanization_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q005_urbanization_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q005_urbanization_year_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q005_urbanization_year_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `b1a37c5d71dac8e1c3df6d1b23ceae1cea5128a3e021555de49e6705dc767512`
- Processed CSV SHA256: `78a1cacc7b38343fff31f7f2b31e6f2d5b96292f569ffba2d6a8d76803b9f6e4`
- Processed parquet SHA256: `b15678f03ed310dda02b0b15c2afdcc5f5cb456f9e0cc6dd9795ef3d87fab71f`
- Notes/caveats path: `data\processed\csv\Q005_urbanization_year_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q006_urbanization_place_mc_g40_g41_2019_2024

- Query ID: `Q006_urbanization_place_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q006_urbanization_place_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q006_urbanization_place_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q006_urbanization_place_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q006_urbanization_place_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `380f745f23d9bf595d4efc30310eef03937b267d8e3210bde0dcef6860c2f851`
- Processed CSV SHA256: `5d1ccc4939170abcc71f54a1263a49c3beed75ae88af505d78f584cda527696b`
- Processed parquet SHA256: `c72a8f47bea56aa8ed8c6e1844ae8d65fdc576f038f145f9b73d37e87b717411`
- Notes/caveats path: `data\processed\csv\Q006_urbanization_place_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q007_urbanization_age_mc_g40_g41_2019_2024

- Query ID: `Q007_urbanization_age_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q007_urbanization_age_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q007_urbanization_age_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q007_urbanization_age_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q007_urbanization_age_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `ce6b2f9a9e9266eefb30ec880d34abb35f5d3ab98148a00bc4fb7b2464497811`
- Processed CSV SHA256: `c3936b9f2ba66d70b5a8825fce19b5bb121ca502ed3fe65331102821e2b66337`
- Processed parquet SHA256: `134993db07364b35bc52662b7ca5a776e80f293687447106acb96d8b61a0b53d`
- Notes/caveats path: `data\processed\csv\Q007_urbanization_age_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q008_urbanization_sex_mc_g40_g41_2019_2024

- Query ID: `Q008_urbanization_sex_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q008_urbanization_sex_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q008_urbanization_sex_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q008_urbanization_sex_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q008_urbanization_sex_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `9bda80263c5484befdc0ab65b4dd74d93e64c7c58746ff9bae571ccc468764b5`
- Processed CSV SHA256: `55fd441009fb078803f79083d25e0dc36ed533f49e3cc46cfae72f1ce7b14c36`
- Processed parquet SHA256: `40cd85262f3e2c6498a5ba9e57e08fc5f2f6b6737316dad41be1a47a3b8a691a`
- Notes/caveats path: `data\processed\csv\Q008_urbanization_sex_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q009a_urbanization_race6_mc_g40_g41_2019_2024

- Query ID: `Q009a_urbanization_race6_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q009a_urbanization_race6_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q009a_urbanization_race6_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q009a_urbanization_race6_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q009a_urbanization_race6_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `bb46bcc404669d75867268b7c2f6083b2d66c5fec112aec511d1267c1eaa8456`
- Processed CSV SHA256: `f0584c7932cccfa198b963d2eb73f4f8349c390bf1820f63e59a76d6fa959a96`
- Processed parquet SHA256: `d7038d81b0d0aeab6d270b8a9259f12ec636a4d594f133a01485fbf5cc28ba33`
- Notes/caveats path: `data\processed\csv\Q009a_urbanization_race6_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q009b_urbanization_hispanic_mc_g40_g41_2019_2024

- Query ID: `Q009b_urbanization_hispanic_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q009b_urbanization_hispanic_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `2193154e6022088298bfbc3734151bedfdaa36fd3cd9cfc387485087235dd1f9`
- Processed CSV SHA256: `b9cb67c9bbf23bdbc120350a374d815812d0131bed30b30df36fad7bcc3b4eb7`
- Processed parquet SHA256: `7250a89c2e6f2ef3fba043568e76f6e09031fef3f6993431fc0848fa19bcd287`
- Notes/caveats path: `data\processed\csv\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024

- Query ID: `Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.xml`
- Raw SHA256: `c69c41b6e3d9a9ec1ebce2ceb25ccf4b384d4615e22a054bf5b58a03a62493f7`
- Processed CSV SHA256: `5def0c55ee90c6f32f8bc3cba553cc6ec9c2e1f036cdd7b8790d9813ca818aa3`
- Processed parquet SHA256: `36e07934d4a833f0acc970b85cafb38d114b4d8212359f123c857460909e0694`
- Notes/caveats path: `data\processed\csv\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q011_state_year_uc_g40_g41_2019_2024

- Query ID: `Q011_state_year_uc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q011_state_year_uc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q011_state_year_uc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q011_state_year_uc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q011_state_year_uc_g40_g41_2019_2024.xml`
- Raw SHA256: `4668211f28d717d75fe936860e1e8ef859be63efbb4d6deb5f4ec1b26b9eb61c`
- Processed CSV SHA256: `64e8036840019e9d66b8b878d426831352215388d68d3bca9926015fd2157952`
- Processed parquet SHA256: `2cc6e167451337ee190bfe5342c1a870c93d3b43f60eae7c6f7e18f0372158cf`
- Notes/caveats path: `data\processed\csv\Q011_state_year_uc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q012_urbanization_year_uc_g40_g41_2019_2024

- Query ID: `Q012_urbanization_year_uc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q012_urbanization_year_uc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q012_urbanization_year_uc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q012_urbanization_year_uc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q012_urbanization_year_uc_g40_g41_2019_2024.xml`
- Raw SHA256: `7331644588c2ef09d38b84152b7de725f8b7aa9fb96e977b1cbbdec4babad43e`
- Processed CSV SHA256: `f445784a951e24d14f9f6fbac7c3aa461f98b70c82f041ed20d52efaf8868b20`
- Processed parquet SHA256: `2f7ea6db5565f9e752a2b148165b344501abb86e249f013e937ec5fa9b1c951e`
- Notes/caveats path: `data\processed\csv\Q012_urbanization_year_uc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q013_national_age_year_mc_g40_g41_2019_2024

- Query ID: `Q013_national_age_year_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q013_national_age_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q013_national_age_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q013_national_age_year_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q013_national_age_year_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `db75c82551527ed3e4a3fec9620ce8bdd224d3bf6c1a27f9f60284ae8ed3772d`
- Processed CSV SHA256: `712c2de35e10f7b71ea2fde61b4763cd6b97e4ba38ef2050aed7627df4f37cf4`
- Processed parquet SHA256: `f2536634bb6cc7b35ae8f55a5643af75593e21ee93a619d3ba390bae4f2d81c0`
- Notes/caveats path: `data\processed\csv\Q013_national_age_year_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed

- Query ID: `Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.xls`
- Processed CSV: `data\processed\csv\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.csv`
- Processed parquet: `data\processed\parquet\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.parquet`
- Request XML path if available: `data\raw\xml_requests\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.xml`
- Raw SHA256: `ac782b0fe9309db73852d67e8aca8ff25d0b1a2a2ce1151db18b1437bba6683c`
- Processed CSV SHA256: `ad6b8e7d53f5c9007d3cc65f77bcc29187ee721cebbea465d1b175c5384e338b`
- Processed parquet SHA256: `2643b6c4fb96e7a4c28d638f4c374f476a3763c6551d325e067c0692cdc3710f`
- Notes/caveats path: `data\processed\csv\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.

### Q015_state_period_mc_g40_g41_2019_2024

- Query ID: `Q015_state_period_mc_g40_g41_2019_2024`
- Database ID: `D157`
- Raw filename: `data\raw\xls\wonder_q015_state_period_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q015_state_period_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q015_state_period_mc_g40_g41_2019_2024.parquet`
- Request XML path if available: `data\raw\xml_requests\Q015_state_period_mc_g40_g41_2019_2024.xml`
- Raw SHA256: `d2609936104d79bacc688c2c3f2b7e7446f47fcc28285da0c27d2549e7539e94`
- Processed CSV SHA256: `ebd0fba176d2e09f3651db7830f30f113ff712a135e5203eea34deb507e24ad7`
- Processed parquet SHA256: `481e8d060473e95225dcc03f1553669abf450bda32d1d9a2e3d0d9623dd2d933`
- Notes/caveats path: `data\processed\csv\Q015_state_period_mc_g40_g41_2019_2024_notes.csv`
- Date/time accessed: see `data\logs\export_events.jsonl` when exports are run.
- Browser version if used: captured by Playwright runtime logs when available.
