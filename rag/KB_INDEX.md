# FarmConnect AI — Knowledge Base Index

This Retrieval-Augmented Generation (RAG) knowledge base contains **106 documents** (**~164,232 words**) across **20 categories**, written as authoritative reference material for African smallholder farmers and buyers. It is indexed automatically by `rag/retriever.py` (hybrid BM25 + TF-IDF search) and grounds every answer FarmConnect AI gives.

> This index is generated for humans. It lives outside `knowledge_base/` so it is not itself indexed for retrieval. Regenerate it with `python -m rag.build_kb_index` whenever documents are added.

## Contents at a glance

| Category | Documents |
|---|---|
| 🌽 Crops | 36 |
| 🦠 Diseases | 18 |
| 🐛 Pests | 13 |
| 🌿 Weeds | 3 |
| 🐄 Livestock | 3 |
| 🪨 Soil | 3 |
| 🧪 Fertilisers | 3 |
| 💧 Irrigation | 2 |
| 🌦️ Weather & Climate | 3 |
| 📅 Planting Calendars | 4 |
| 🌾 Harvesting | 1 |
| 📦 Storage | 3 |
| ♻️ Sustainability | 1 |
| 🛒 Marketplace | 3 |
| 💰 Pricing | 2 |
| 📋 Regulations | 2 |
| 🚨 Emergency Guides | 2 |
| 🔧 Troubleshooting | 1 |
| ❓ FAQs | 1 |
| 🤖 AI Guidelines | 2 |
| **Total** | **106** |

## 🌽 Crops

- **Avocado** — `crops/avocado.md`
- **Banana and Plantain** — `crops/banana_and_plantain.md`
- **Barley** — `crops/barley.md`
- **Cabbage** — `crops/cabbage.md`
- **Carrot** — `crops/carrot.md`
- **Cassava** — `crops/cassava.md`
- **Chilli Pepper** — `crops/chilli_pepper.md`
- **Citrus / Orange** — `crops/citrus_orange.md`
- **Cocoa** — `crops/cocoa.md`
- **Coffee** — `crops/coffee.md`
- **Common Beans** — `crops/common_beans.md`
- **Cotton** — `crops/cotton.md`
- **Cowpea** — `crops/cowpea.md`
- **Cucumber** — `crops/cucumber.md`
- **Eggplant** — `crops/eggplant.md`
- **Finger Millet** — `crops/finger_millet.md`
- **Garlic** — `crops/garlic.md`
- **Groundnut (Peanut)** — `crops/groundnut.md`
- **Irish Potato** — `crops/irish_potato.md`
- **Kale (Sukuma Wiki)** — `crops/kale_sukuma_wiki.md`
- **Maize (Corn)** — `crops/maize.md`
- **Mango** — `crops/mango.md`
- **Okra** — `crops/okra.md`
- **Onion** — `crops/onion.md`
- **Papaya / Pawpaw** — `crops/papaya_pawpaw.md`
- **Pearl Millet** — `crops/pearl_millet.md`
- **Pumpkin** — `crops/pumpkin.md`
- **Rice** — `crops/rice.md`
- **Sorghum** — `crops/sorghum.md`
- **Soybean (Soya Bean)** — `crops/soybean.md`
- **Spinach** — `crops/spinach.md`
- **Sweet Pepper** — `crops/sweet_pepper.md`
- **Sweet Potato** — `crops/sweet_potato.md`
- **Tea** — `crops/tea.md`
- **Tomato** — `crops/tomato.md`
- **Wheat** — `crops/wheat.md`

## 🦠 Diseases

- **Banana Xanthomonas Wilt** — `diseases/banana_xanthomonas_wilt.md`
- **Bean Anthracnose** — `diseases/bean_anthracnose.md`
- **Cassava Brown Streak Disease** — `diseases/cassava_brown_streak_disease.md`
- **Cassava Mosaic Disease** — `diseases/cassava_mosaic_disease.md`
- **Common Rust of Maize** — `diseases/maize_common_rust.md`
- **Early Blight of Tomato** — `diseases/tomato_early_blight.md`
- **Fusarium Wilt of Tomato** — `diseases/fusarium_wilt_tomato.md`
- **Grey Leaf Spot of Maize** — `diseases/grey_leaf_spot_maize.md`
- **Groundnut Rosette Disease** — `diseases/groundnut_rosette_disease.md`
- **Maize Ear Rots** — `diseases/maize_ear_rots.md`
- **Maize Lethal Necrosis** — `diseases/maize_lethal_necrosis.md`
- **Maize Streak Virus Disease** — `diseases/maize_streak_virus.md`
- **Northern Leaf Blight of Maize** — `diseases/northern_leaf_blight_maize.md`
- **Rice Blast** — `diseases/rice_blast.md`
- **Septoria Leaf Spot of Tomato** — `diseases/septoria_leaf_spot_tomato.md`
- **Tomato Bacterial Wilt** — `diseases/tomato_bacterial_wilt.md`
- **Tomato Late Blight** — `diseases/tomato_late_blight.md`
- **Tomato Yellow Leaf Curl Virus** — `diseases/tomato_yellow_leaf_curl_virus.md`

## 🐛 Pests

- **African Bollworm** — `pests/african_bollworm.md`
- **Aphids** — `pests/aphids.md`
- **Bruchids (Pulse Beetles)** — `pests/bruchids.md`
- **Cutworms** — `pests/cutworms.md`
- **Desert Locust** — `pests/desert_locust.md`
- **Fall Armyworm** — `pests/fall_armyworm.md`
- **Grain Weevils and Borers** — `pests/grain_weevils_and_borers.md`
- **Larger Grain Borer** — `pests/larger_grain_borer.md`
- **Maize Stalk Borer** — `pests/maize_stalk_borer.md`
- **Termites** — `pests/termites.md`
- **Thrips** — `pests/thrips.md`
- **Tomato Leafminer (Tuta absoluta)** — `pests/tomato_leafminer_tuta_absoluta.md`
- **Whitefly** — `pests/whitefly.md`

## 🌿 Weeds

- **General Weed Management Principles** — `weeds/general_weed_management.md`
- **Nutsedge and Couch Grass** — `weeds/nutsedge_and_couch_grass.md`
- **Striga (Witchweed)** — `weeds/striga.md`

## 🐄 Livestock

- **Goats, Sheep, and Cattle for Smallholders** — `livestock/goats_sheep_and_cattle.md`
- **Livestock Health and Biosecurity** — `livestock/livestock_health_and_biosecurity.md`
- **Small-Scale Poultry Keeping (Chickens)** — `livestock/poultry_keeping.md`

## 🪨 Soil

- **Major Soil Types in Africa and Their Agricultural Characteristics** — `soil/soil_types_africa.md`
- **Soil Conservation and Erosion Control** — `soil/soil_conservation_and_erosion.md`
- **Soil Testing and Fertility Management** — `soil/soil_testing_and_fertility.md`

## 🧪 Fertilisers

- **Fertiliser Basics** — `fertilisers/fertiliser_basics.md`
- **Nutrient Deficiencies Guide: Visual Diagnosis** — `fertilisers/nutrient_deficiencies_guide.md`
- **Organic Fertilisers and Soil Amendments** — `fertilisers/organic_fertilisers.md`

## 💧 Irrigation

- **Irrigation Methods and Water Management** — `irrigation/irrigation_methods.md`
- **Irrigation Scheduling: When and How Much to Water** — `irrigation/irrigation_scheduling.md`

## 🌦️ Weather & Climate

- **Climate-Smart Agriculture** — `weather/climate_smart_agriculture.md`
- **Drought and Flood Management** — `weather/drought_and_flood_management.md`
- **Weather Impacts on Farming** — `weather/weather_impacts_on_farming.md`

## 📅 Planting Calendars

- **Regional Planting Calendar: Central Africa** — `planting_calendars/central_africa_calendar.md`
- **Regional Planting Calendar: East Africa** — `planting_calendars/east_africa_calendar.md`
- **Regional Planting Calendar: Southern Africa** — `planting_calendars/southern_africa_calendar.md`
- **Regional Planting Calendar: West Africa** — `planting_calendars/west_africa_calendar.md`

## 🌾 Harvesting

- **Harvesting Best Practices** — `harvesting/harvesting_best_practices.md`

## 📦 Storage

- **Aflatoxin Prevention** — `storage/aflatoxin_prevention.md`
- **Grain Storage** — `storage/grain_storage.md`
- **Perishable Crop Storage (Fruits, Vegetables, and Root Crops)** — `storage/perishable_storage.md`

## ♻️ Sustainability

- **Sustainable and Climate-Smart Farming Practices** — `sustainability/sustainable_farming_practices.md`

## 🛒 Marketplace

- **Agricultural Market Fundamentals** — `marketplace/market_fundamentals.md`
- **Buyer Preferences and Seasonal Demand** — `marketplace/buyer_preferences_and_seasonal_demand.md`
- **Product Grading and Quality Standards** — `marketplace/product_grading_and_quality.md`

## 💰 Pricing

- **Fair Pricing Principles** — `pricing/pricing_principles.md`
- **Price Negotiation and Value Addition** — `pricing/price_negotiation_and_value_addition.md`

## 📋 Regulations

- **Agricultural Regulations Overview** — `regulations/agricultural_regulations_overview.md`
- **Pesticide Safety and Handling** — `regulations/pesticide_safety_and_handling.md`

## 🚨 Emergency Guides

- **Crop Emergency Guide** — `emergency_guides/crop_emergency_guide.md`
- **Pest Outbreak Emergency Guide** — `emergency_guides/pest_outbreak_emergency_guide.md`

## 🔧 Troubleshooting

- **Crop Troubleshooting Guide** — `troubleshooting/crop_troubleshooting_guide.md`

## ❓ FAQs

- **General Farming Frequently Asked Questions** — `faqs/general_farming_faqs.md`

## 🤖 AI Guidelines

- **AI Safety Guidelines for FarmConnect** — `ai_guidelines/ai_safety_guidelines.md`
- **Response Confidence and Uncertainty Guidelines** — `ai_guidelines/response_confidence_and_uncertainty.md`
