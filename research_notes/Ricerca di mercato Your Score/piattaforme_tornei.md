# Tournament management platforms in racket sports: possible partners for a "result entry + signed scoresheet" module

Research date: 22 Oct 2026. Method: about 18 web searches and fetches. Limits: raqt.com and pickleball.com could not be fetched directly (DNS failure / proxy 403), so RAQT and pickleball.com facts come from search snippets, app-store listings and help-centre URLs. Some search results were summaries written by the search tool, so the claims below should be re-checked on the primary page before external use. Anything marked "UNVERIFIED (prior knowledge)" comes from the researcher's training knowledge, not from a source fetched in this session.

## 1. RAQT (Raqt Svenska AB): company, product, federations, score entry, API

### Takeaway
RAQT is a small Swedish company (2-10 staff, founded 2017). Its pickleball platform runs the federation's Swedish Pickleball Tour, including the 2026 Swedish Championships. It offers registration, automated draws, live scoring, live tournament feeds, visual brackets and integrated DUPR updates. No public developer or API documentation was found. RAQT looks like a realistic first partner: a small team, federation-backed, with a gap in on-site "official" result capture. Its API and current score-entry flow must be confirmed directly with the company.

### Cited Findings
- **App.** The app's App Store developer is Raqt Svenska AB. The listing reads "Build your pickleball profile, register matches, and set up your events in chat." Recent versions added a redesigned UI, email login, a visual bracket view for tournaments, and live feeds for tournaments and classes. Only about 2 ratings are shown, so the app has a small rating base. — [App Store](https://apps.apple.com/us/app/raqt-pickleball-family-friends/id1617653147)
- **Android and address.** The Google Play listing (package `com.boilerplatee`) describes the app as a way to register for tournaments and collect ranking points locally. Company address: Våtmarksvägen 14, 186 55 Vallentuna, Sweden. — [Google Play](https://play.google.com/store/apps/details?id=com.boilerplatee&hl=en_US)
- **Organizer offer.** The organizers page offers clubs and federations registration, automated draws, live scoring and integrated DUPR updates. It lists Pickleballförbundet (the Swedish Pickleball Federation) among partner organizers. — [RAQT Organizers](https://raqt.com/en/organizers) (seen via search snippet; the page could not be fetched)
- **Swedish Pickleball Tour.** The tour is organized by Pickleballförbundet on RAQT, and its calendar includes Svenska Mästerskapen (Swedish Championships) 2026. — [RAQT Tour 1](https://raqt.com/en/tour/1); also white-labelled at [swedishpickleballopen.org](https://swedishpickleballopen.org/tour/1)
- **White-label domain.** swedishpickleballopen.org serves the RAQT sign-in and tour pages, which suggests RAQT already does white-label or custom domains for events. — [swedishpickleballopen.org](https://www.swedishpickleballopen.org/)
- **Company profile.** LinkedIn lists RAQT as privately held, founded 2017, 2-10 employees, industry "Spectator Sports". — [LinkedIn Raqt](https://www.linkedin.com/company/raqt)
- **Scheduling engine.** RAQT launched a dynamic, automated scheduling engine for large pickleball tournaments. A post by Jens Larsson says it scheduled 6,500 matches in 10 minutes. — [Jens Larsson LinkedIn](https://se.linkedin.com/in/jensflarsson)
- **Sweden in the international circuit.** The APP (Association of Pickleball Players) partnered with Pickleball Sweden for the Gamma Sweden Open, so Sweden hosts international-circuit events. — [Pickleball Union](https://pickleballunion.com/app-pickleball-sweden-open/)

### Inferences
- **Score entry today.** "Register matches" in the app plus "live scoring" for organizers suggests scores are entered by players and/or the tournament desk in the RAQT app. No evidence was found of a signed or verified scoresheet, or of a dedicated referee app. That is the gap Your Score would fill.
- **DUPR dependency.** DUPR integration means RAQT already pushes results to DUPR through the DUPR partner API. A signed scoresheet improves the integrity of DUPR-rated results, which is a selling point.
- **Integration approach.** With a 2-10 person team, RAQT is more likely to accept an embedded or plug-in module than to build its own. Expect integration through a private API or webhook co-developed with them.

### Gaps
- **Founders and funding.** No founder was confirmed (Jens Larsson is strongly linked to the product but not confirmed as founder). No funding rounds were found.
- **Web API.** The brief mentions a RAQT "Web API". No documentation was found by search and raqt.com was unreachable. It is unknown whether the API is public, read-only or has write access.
- **Countries and federations.** Coverage beyond Sweden is unconfirmed (other Nordic or EU federations?).
- **Scale and pricing.** Tournament and user counts were not found. Pricing to organizers was not found.
- **Ownership.** Avoid confusion with RAQTO, an unrelated Brazilian startup founded by Gabriel Luz. — [abes.org.br](https://abes.org.br/en/?p=109351)

## 2. pickleball.com (Pickleball Inc.: PickleballBrackets, PickleballTournaments, Referee App, PPA ecosystem)

### Takeaway
Pickleball Inc. already covers the full on-court scoring workflow in-house: a dedicated Referee App, player self-scoring with confirmation, and a "Live Console" that auto-runs courts. No public developer API was found. It is a strong US incumbent and a competitor more than a likely buyer. Partnership potential is low unless Your Score offers something it lacks, such as legally signed scoresheets or EU / GDPR compliance.

### Cited Findings
- **Referee App access.** The app is password-protected. Referees log in with pickleball.com credentials, and the tournament director issues a tourney code and a ref code from the Edit Tourney menu. — [pickleball.com docs: How to Use the Referee App](https://pickleball.com/docs/en/72000647302-how-to-use-the-referee-app); [Freshdesk mirror](https://pickleball.freshdesk.com/en/support/solutions/articles/72000647302-how-to-use-the-referee-app)
- **Referee App scoring.** It records rally-by-rally points, side-outs and server changes, and has a Training Mode. Scores feed the tournament site. The store listings say it "merges seamlessly" with PickleballBrackets.com and PickleballTournaments.com. — [Google Play Referee App](https://play.google.com/store/apps/details?id=com.pickleball.refscoring&hl=en_US); [App Store](https://apps.apple.com/us/app/id1666312041)
- **Player scoring.** Players enter scores when no referee is assigned. Where there is a referee, the player still enters the score but the ref oversees it. In Live Console "Auto-Run", as scores are entered and confirmed, the system assigns the next matches to freed courts. — [pickleball.com docs: Player scoring & Auto-Run](https://pickleball.com/docs/en/72000646262-how-to-enable-player-scoring-and-auto-run-your-tournament)
- **Promotion to organizers.** pickleball.com actively pushes the Referee App to tournament directors. — [pickleball.com blog](https://pickleball.com/blogs/take-advantage-of-the-referee-app-why-you-should-use-this-now-1)
- **Pricing.** PickleballTournaments charges a one-time setup fee of $25 per new tournament. Optional US texting costs $0.25 per player. — summary of pickleball.com help content from search (exact page URL not captured; check on [pickleball.com docs](https://pickleball.com/docs/en/api/v1/public/post/72000615191))
- **Scale.** pickleball.com lists about 1.2k active tournaments. — [pickleball.com blogs](https://pickleball.com/blogs/3)
- **DUPR.** Pickleball Inc. adopted DUPR as exclusive rating provider for PickleballBrackets, pickleball.com and PickleballTournaments (announced 2024). Organizers can seed by DUPR. — [DUPR blog](https://www.dupr.com/post/pickleballbrackets-pickleball-com-and-pickleball-tournaments-align-with-dupr-marking-a-major-step-forward-for-the-growth-of-the-game); [pickleball.com docs: PT and DUPR](https://pickleball.com/docs/en/article/does-pickleball-tournaments-pt-integrate-with-dupr.md)
- **No public API found.** The URL path `/docs/en/api/v1/public/` hosts help-centre articles, not an API reference. Only an unofficial Apify scraper exists for pickleball.com data (PPA standings). — [Apify actor](https://apify.com/fingolfin/pickleball-data-api.md)
- **Other US tools.** R2 Sports markets pickleball tournament software and claims USAPA-approved status. — [R2 Sports](https://www.r2sports.com/cart/files/84/Pickleball-Tournament-Software.asp)

### Inferences
- **Same feature, already built.** Pickleball Inc. has the same core feature (court-side scoring tied to brackets), so a white-label sale is unlikely. A possible angle is a "certified / signed result" layer for sanctioned events, or EU events run on PickleballBrackets.
- **Hard to integrate.** Because there is no public write API, any integration would need a business-development deal.

### Gaps
- **PPA usage.** Whether PPA Tour uses this Referee App or a separate pro system was not confirmed.
- **Opponent confirmation.** Whether player scores must be confirmed by the opponent, versus by the tournament desk, was not confirmed (the docs say "entered and confirmed").
- **API or partner programme.** No developer API or partner programme was found.

## 3. DUPR: score submission API and partner ecosystem

### Takeaway
DUPR runs a closed partner API: it says it has more than 70 API partners, and access goes through an account manager. Clubs without a software partner upload results manually or by CSV. Your Score would gain from becoming a DUPR API partner itself, or from integrating through host platforms like RAQT. Signed scoresheets fit DUPR's interest in verified results.

### Cited Findings
- **Club Resources page.** DUPR lists more than 70 API partners, including Pickleball Tournaments, CourtReserve and Reclub. Without a software partner, clubs "enter results directly to the club through the standard upload or the CSV template". Clubs contact their account manager to connect a club ID so results upload automatically. — [DUPR Club Resources](https://www.dupr.com/club-resources); [DUPR Clubs](https://www.dupr.com/clubs)
- **Courtly (India, Aug 2026).** Courtly's tournament system sends matches to DUPR directly, so DUPR submission is fully automated. Casual games are also fed into official ratings. — [Business Standard / ANI](https://www.business-standard.com/content/press-releases-ani/dupr-and-courtly-partner-to-bring-verified-global-ratings-and-level-based-play-to-every-court-126082001278_1.html); [MediaBrief](https://mediabrief.com/courtly-partners-with-dupr-to-integrate-official-pickleball-ratings-into-its-platform/)
- **PlayerU.** PlayerU announced full API integration with DUPR for real-time ratings and match tracking. — [DUPR blog](https://www.dupr.com/post/playeru-partners-with-dupr-to-offer-realtime-match-tracking-and-analytics)
- **Subscores.** DUPR said Subscores and Career High would be made available to API partners (announced as a future rollout). — [DUPR blog](https://www.dupr.com/post/new-dupr-features-to-help-you-understand-your-game)
- **Playtomic.** Playtomic partnered with DUPR to embed verified ratings for level-based open matches. — [DUPR blog](https://www.dupr.com/post/playtomic-partners-with-dupr-to-power-the-next-era-of-community-driven-pickleball)
- **Earlier deal.** Lucra signed a deal with DUPR in 2023. — [BusinessWire](https://www.businesswire.com/news/home/20230816419793/en/Lucra-Signs-Landmark-Deal-with-DUPR---The-Global-Rating-System-of-Pickleball-The-Official-Platform-of-Major-League-Pickleball)

### Inferences
- **Effectively a marketplace.** DUPR's partner list works as a de facto integration directory in pickleball. Being listed there would add credibility.

### Gaps
- No public API docs (endpoints, authentication, fees) were found.
- DUPR's requirements for "verified" results were not found, so it is unknown whether signatures add rating weight.

## 4. OpenPlay

### Takeaway
No platform called "OpenPlay" (openplay.io or similar) could be identified as a tournament engine. Searches only return "open play" as a session format, for example Playtomic's Open Play programs for US clubs. The caller should confirm the exact product, URL or company.

### Cited Findings
- **Playtomic Open Play.** Playtomic Manager has an "Open Play Programs" feature, currently only for US clubs. — [Playtomic Help](https://helpmanager.playtomic.com/hc/en-gb/articles/44504259363089-Introducing-Open-Play-Programs-in-Playtomic-Manager-U-S-Clubs); [How to launch Open Play](https://helpmanager.playtomic.com/hc/en-gb/articles/47364176124305-How-to-launch-Open-Play-at-your-pickleball-club)
- **OpenSports.** A similarly named platform, OpenSports (Toronto), handles leagues, tournaments, registrations and payments. — [CB Insights](https://www.cbinsights.com/compare/opensports-vs-pickleball-tournament); [Software Advice](https://www.softwareadvice.co.uk/software/315621/opensports)
- **Other pickleball apps with DUPR sync.** PKL App (PKL Technologies LLC) and Pikel both advertise DUPR sync. — [mwm.ai PKL](https://mwm.ai/apps/pkl-app/6759809423)

### Gaps
- OpenPlay's identity, owner, features and API are all unknown.

## 5. European padel and tennis platforms: Rankedin, Playtomic, Matchi, Tournamentsoftware (Visual Reality), Padel Fast, Score7, PadelMix

### Takeaway
Two platforms in this group are federation-grade:
- **Rankedin** (Norway): official software of the Argentine Padel Federation, and its data is used by third-party apps.
- **Tournamentsoftware / Visual Reality** (Netherlands): used by BWF, Squash Canada and Badminton & Tennis Canada, with on-site live-score modules.

Playtomic has light tournament formats (Americano, Mexicano, King of the Court) and no official public API found. No public write APIs were found for any of them. Pricing was not publicly found for Rankedin or Tournamentsoftware.

### Cited Findings
- **Rankedin – Argentina.** Norwegian company RankedIn was selected by the Federación Argentina de Pádel as its digital partner, for all players and clubs and for national and club-level events. — [Padel Addict](https://www.padeladdict.com/la-federacion-argentina-de-padel-elige-a-rankedin-como-el-software-oficial/)
- **Rankedin – data reuse.** The PadelRanks app pulls live data from Rankedin and Playtomic across 18 countries. That suggests some data access, but the method is unknown (official API or scraping). — [mwm.ai PadelRanks](https://mwm.ai/apps/padelranks/6767493195)
- **Visual Reality – events.** The platform has been used at World Squash Championships, the Davis Cup and Olympic badminton. Clients include the Badminton World Federation (BWF), and Badminton Canada and Tennis Canada are transitioning to it. — [Squash Canada](https://squash.ca/news/squash-canada-announces-partnership-with-world-leading-tournament-software-platform/)
- **Visual Reality – live scores.** It has a module that processes results and shows live scores on-site and online. — [toernooi.nl products](https://producten.toernooi.nl/en/)
- **Cup2000.** The Danish Badminton Federation uses Cup2000, which has automatic live score. — [cup2000.com](https://www.cup2000.com/tournament-software/)
- **Playtomic – tournaments.** Playtomic has built-in tournament tools for King of the Court, Americano and Mexicano, with automated pairings and leaderboards. — [Playtomic Help](https://helpmanager.playtomic.com/hc/en-gb/articles/44129657203985-New-Tournament-Tools-King-of-the-Court-Americano-and-Mexicano)
- **Playtomic – API.** Only an unofficial MCP connector exposes Playtomic tournaments and leagues data. No official API was found. — [anythingmcp](https://anythingmcp.com/guides/playtomic-now-on-anythingmcp)
- **Matchi.** No information was found on a Matchi API or partner programme.
- **UNVERIFIED (prior knowledge).** These points were not checked in this session:
  - Tournamentsoftware.com offers federations a web-service / API for rankings and results. Many national tennis and badminton federations use it (for example Netherlands KNLTB and Badminton Europe events).
  - Matchi (Sweden) is a booking platform for padel, tennis and badminton, focused on the Nordics.
  - Padel Fast, Score7 and PadelMix are lightweight tournament generators (brackets, Americano) aimed at clubs.

### Inferences
- **Federation platforms (Rankedin, Visual Reality).** They are the best "plug-in" targets after RAQT. They serve federations that care about result integrity, but sales cycles will be longer.
- **Playtomic.** It is club and social-focused. A signed scoresheet matters less for Americano formats, so potential is lower.

### Gaps
- **Padel Fast, Score7, PadelMix.** Not researched (limited tool budget). Owners, APIs and pricing are unknown.
- **Pricing.** Rankedin, Tournamentsoftware and Matchi pricing to organizers was not found.
- **Partner programmes.** None were found for Rankedin, Tournamentsoftware or Matchi.

## 6. Italy (FITP / MyFITP / TPRA / Wansport), Tennis Europe / ITF, Swiss and German platforms

### Takeaway
In Italy, FITP centralizes entries through MyFITP / Portale Unico Competizioni and the TPRA portal (tpra.it). Results are published there first and then pushed to partner apps such as Wansport. In some team competitions, results are entered by the home captain and only count once both teams confirm. That is essentially a digital "two-party signature" model done by hand, and it validates the Your Score concept. FITP is a federation monopoly, so it is a possible institutional customer rather than a SaaS partner.

### Cited Findings
- **MyFITP for entries.** For 2026 beach tennis, entries go exclusively through the federal portal MyFITP, which is part of the Portale Unico Competizioni on fitp.it. — [FITP Beach Tennis 2026 regulation](https://www.fitp.it/media/FIT/Federtennis/Beach_Tennis/Campionati/20260807_Cervia_Regolamento_fitp.pdf); [FITP Beach Tennis base activity 2026](https://www.fitp.it/media/Files/20260203_BEACH_TENNIS.PRESENTAZIONE_ATTIVITA__DI_BASE_2026.aggiornamento.30.01.26.pdf)
- **TPRA portal.** FITP-TPRA tournament entries go through the TPRA portal. In 2025, intra-club stages were managed via the "Connect Hub – TPRA – FITP Junior Program gestione tornei". — [TPRA 2023 regulation](https://fitp.it/media/FIT/Federtennis/Siti_regionali/Lombardia/File_pdf/20230130_CAMPIONATO_ITALIANO_INDIVIDUALE_FITJP___TPRA_2023.pdf); [TPRA 2025 regulation](https://fitp.it/media/CARICAMENTO_IMMAGINI/20241016_campionato_italiano_individuale_fitjp___tpra_2025_new_1.pdf)
- **Coppa Italia Padel 2024.** Results are entered by the host team's captain, and points are not awarded until both teams confirm. — [TPRA Coppa Italia Padel 2024](https://www.fitp.it/media/FIT/Federtennis/Siti_regionali/Liguria/Immagini/2023/20240313_TPRA___REGOLAMENTO_COPPA_ITALIA_PADEL_2024.pdf)
- **Decathlon Wansport Padel Cup 2026.** Groups, standings and results are published first on tpra.it and then in the Wansport app. Matches are played at FITP-affiliated clubs using the Wansport booking platform. — [Regolamento Decathlon Wansport Padel Cup](https://wpc.wansport.com/wp-content/uploads/2026/03/Regolamento-Decathlon-Wansport-Padel-Cup-1.pdf); [Wansport App Store](https://apps.apple.com/app/id6445919117)
- **Officials' workstations.** Older TPRA regulations require a workstation for officials (computer, printer, internet) only in SGAT-procedure competitions and national championships. — [FITP TPRA regulation 2021](https://www.fitp.it/media/FIT/Federtennis/Siti_regionali/Veneto/File_pdf/20210309_Regolamento_FITJP_TPRA_INDIVIDUALE.pdf)
- **Players as umpires.** Beach tennis players may be required, at the referee's request, to umpire at least one match per day. — same FITP beach-tennis regulations as above
- **MyFITP app.** The app offers tournament entry (including TPRA), match statistics and rankings. — [mwm.ai MyFITP](https://mwm.ai/apps/myfitp/1474356278)
- **TPRA padel general regulation.** — [tpra.fitp.it](https://tpra.fitp.it/File/REGOLAMENTO%20GENERALE%20PADEL%20-%20AGGIORNAMENTO_100223.pdf)

### Inferences
- **FITP partners.** Wansport is an example of a private app downstream of FITP / TPRA data. It could be an Italian channel partner, or an Italian equivalent of RAQT.
- **Two-party confirmation.** The "both teams confirm" rule shows FITP already requires two-party result validation. A court-side signed scoresheet could digitize the paper referto (scoresheet) and SGAT workflows.

### Gaps
- No FITP referee or result-entry app was found, and no public FITP API.
- Tennis Europe and ITF systems were not researched. UNVERIFIED (prior knowledge): ITF and Tennis Europe use their own IPIN-based systems.
- Swiss and German platforms (Swiss Tennis "MyTennis", DTB / nuLiga, mybigpoint) were not researched. UNVERIFIED (prior knowledge): nuLiga (nu Datenautomaten GmbH) runs German, Swiss and Austrian tennis leagues and has online result entry by team captains.
- Wansport's ownership, API and pricing were not found.

## 7. Open APIs, partner programmes, marketplaces, and pricing to organizers (cross-platform)

### Takeaway
No platform in scope publishes an open write API for results:
- **DUPR** runs a closed partner API with more than 70 partners. Its partner list is the closest thing to a marketplace.
- **pickleball.com, RAQT, Rankedin, Playtomic and Tournamentsoftware**: no public developer docs were found.

Public pricing is scarce. The data points found are pickleball.com's $25 per tournament plus $0.25 per player for texting, and benchmarks from generic tournament software.

### Cited Findings
- **DUPR.** Partner API with more than 70 partners. Clubs connect through their account manager, with a CSV fallback. — [DUPR Club Resources](https://www.dupr.com/club-resources)
- **pickleball.com pricing.** $25 one-time per tournament, texting $0.25 per player (US). — search summary of pickleball.com help content (see §2)
- **BP-Pickleball pricing.** Pay per event, per player or per season, "as low as $2 per player". — [GetApp](https://www.getapp.com/all-software/a/pickleball-league-and-tournament-management-software/)
- **Generic benchmarks.**
  - Tournify: free up to 8 teams, then €40 or €120 per event, or a yearly subscription. — [Tournify pricing](https://tournifyapp.com/pricing)
  - TourneyStation: from $12 per tournament. — [SourceForge](https://sourceforge.net/software/product/TourneyStation/)
- **PadelOS.** Uses a transaction model with a player-side service fee. — [G2 PadelOS pricing](https://www.g2.com/products/padelos/pricing)

### Inferences
- **Go-to-market.** Integrations will be bilateral deals, not self-serve.
- **Revenue models.**
  - Per-match or per-event fees passed through the host platform: about €0.10-0.50 per match, or a per-event add-on comparable to the $25 setup fees.
  - Rev-share with the host.
  - A federation licence for certified events.
  These figures are the researcher's estimate, not market data.

### Gaps
- No pricing found for RAQT, Rankedin, Tournamentsoftware, Matchi, Playtomic tournaments or Wansport.
- No formal integration marketplace found in racket-sports tournament software.
