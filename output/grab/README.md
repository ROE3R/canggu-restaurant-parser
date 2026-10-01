# GrabFood Output

- `grabfood.csv` / `grabfood.json` — 863 merchant GrabFood area Canggu (link 100%, rating 789, ads/preferred 165, promo).
- `grab_only_no_maps.csv` / `.json` — 786 merchant Grab yang TIDAK ter-match ke dataset Google Maps (match_confidence=grab_only).

Matching Grab→Maps: nama ternormalisasi + area gate (lihat docs/METHODOLOGY.md).
57 merchant ter-match — datanya (rating/votes/ads) menyatu di kolom `grab_*` pada `../canggu_restaurants.csv`.
