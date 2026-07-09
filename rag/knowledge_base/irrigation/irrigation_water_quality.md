# Irrigation Water Quality: Assessing Water for Safe and Effective Use

## Overview
Not all water is equally suitable for irrigation. Water quality affects crop growth, soil health, irrigation equipment performance, and food safety. Poor-quality water can cause salt buildup in soil, clog drip emitters, damage sensitive crops, or introduce contamination risks to food crops. This document explains the main water quality concerns for irrigation - salinity, pH, and contaminants - and how to assess and manage them. For irrigation system selection, see `irrigation/irrigation_methods.md`; for drip-specific clogging concerns, see `irrigation/drip_irrigation_deep_dive.md`; for groundwater sourcing, see `irrigation/borehole_and_well_management.md`.

## Why Water Quality Matters for Irrigation
- Salts and minerals dissolved in irrigation water accumulate in the soil over time if not adequately leached, reducing soil fertility and crop yield.
- Certain water chemistry (high sodium relative to calcium and magnesium) can degrade soil structure, reducing infiltration and aeration.
- Sediment, organic matter, and mineral precipitates in water can clog drip emitters and sprinkler nozzles, reducing irrigation uniformity and system lifespan.
- Biological or chemical contaminants in irrigation water can pose food safety risks, particularly for crops eaten raw or with edible parts in direct contact with water or soil.
- Some crops are far more sensitive to water quality issues (particularly salinity) than others, so acceptable water quality depends partly on what is being grown.

## Key Water Quality Parameters

### Salinity (Electrical Conductivity, EC)
- Salinity is commonly measured as electrical conductivity (EC), since dissolved salts increase water's ability to conduct electricity.
- Higher EC indicates a higher concentration of dissolved salts, which can draw water away from plant roots (osmotic stress) and, over time, accumulate salts in the soil profile.
- Crop tolerance to salinity varies widely: some crops (e.g., barley, certain forage grasses) tolerate moderate salinity reasonably well, while others (e.g., many vegetables, fruit trees, and legumes) are more sensitive and show yield loss at lower salinity levels.
- Soil texture and drainage influence how much salinity risk a given water EC poses: well-drained soils allow salts to be leached below the root zone more easily than poorly drained soils, where salts tend to accumulate.
- Where irrigation water is known or suspected to be moderately saline, periodic leaching (applying enough extra water to flush accumulated salts below the root zone) and selecting more salt-tolerant crops or varieties can help manage the risk.

### Sodium Hazard (Sodium Adsorption Ratio, SAR)
- Beyond total salinity, the relative proportion of sodium compared to calcium and magnesium in irrigation water affects soil structure.
- Water high in sodium relative to calcium and magnesium can cause soil particles to disperse, degrading soil structure, reducing infiltration, and causing crusting - a problem sometimes referred to as a sodium hazard, commonly assessed using the Sodium Adsorption Ratio (SAR).
- Soils with significant clay content are generally more vulnerable to structural damage from high-sodium water than sandy soils.
- Gypsum (calcium sulfate) is sometimes applied to counteract sodium-related soil structure problems by supplying calcium to displace sodium on soil particles, though this should be guided by a soil and water test rather than applied speculatively.

### pH
- Irrigation water pH affects nutrient availability in the soil and, over time with sustained use, can shift soil pH, particularly in soils with low buffering capacity.
- Most crops grow best within a moderate soil pH range (commonly close to neutral, with some variation by crop); consistently very acidic or very alkaline irrigation water can push soil pH outside the optimal range over repeated seasons.
- Very alkaline water can also contribute to scale (mineral deposit) formation in irrigation equipment, particularly drip emitters, alongside a high concentration of calcium and bicarbonate.
- pH problems are generally addressed by monitoring soil pH over time and applying appropriate soil amendments (see `soil/soil_testing_and_fertility.md`) rather than treating the water in isolation.

### Sediment and Turbidity
- Suspended sediment (sand, silt, clay particles) in surface water sources is a primary cause of emitter and nozzle clogging in drip and sprinkler systems.
- High turbidity water generally requires more intensive filtration before use in drip systems; sand and media filters or settling basins are common approaches for sediment-heavy surface water.
- Sediment carried onto crop surfaces by irrigation water (especially by overhead methods) can also be a food safety consideration if the sediment source is contaminated.

### Biological Contaminants
- Irrigation water drawn from surface sources (rivers, ponds, open canals) can carry pathogens from human or animal waste upstream, posing food safety risks especially for crops eaten raw or where water directly contacts edible parts.
- Risk is generally higher for surface water than for properly protected groundwater (see `irrigation/borehole_and_well_management.md` for protecting wells and boreholes from contamination).
- Risk also depends on the irrigation method and timing relative to harvest: methods that avoid wetting the edible portion of the crop (such as drip irrigation at the root zone) and longer intervals between the last irrigation and harvest reduce food safety risk compared to overhead irrigation applied close to harvest.
- Where contamination is suspected or water is drawn from a source with known upstream waste inputs, avoid using that water on crops that will be eaten raw without further treatment, and seek water quality testing.

### Chemical Contaminants
- Agricultural runoff carrying pesticide or fertilizer residues, industrial discharge, and mining runoff are potential sources of chemical contamination in surface water and, in some cases, groundwater.
- Chemical contamination is not always visible or detectable by taste or smell, so water from sources near industrial, mining, or intensive agricultural activity upstream warrants particular caution and testing where contamination is plausible.
- Heavy metal contamination, where present, can accumulate in soil over repeated irrigation and, in some cases, in crops, making it a longer-term as well as immediate concern.

## Simple Field Indicators (and Their Limits)
- **Taste and smell**: unusual salty, metallic, or chemical taste/smell can indicate a water quality problem, but many contaminants (including some pathogens and dissolved salts at moderate levels) are undetectable this way.
- **Clarity**: visibly cloudy or turbid water indicates sediment that will likely cause clogging issues in fine-filtered systems like drip irrigation, though clear water is not automatically free of dissolved salts or biological contamination.
- **Source observation**: water drawn immediately downstream of population centres, livestock concentration areas, or industrial sites carries a higher plausible contamination risk than water from a protected, upstream, or groundwater source.
- **Scale or residue**: white mineral crusting around pipe outlets, emitters, or on soil surfaces after irrigation can indicate high salinity or hardness.
- These field indicators are useful for triage but cannot replace laboratory or field-kit water testing when a real question of crop safety, salinity management, or clogging cause needs to be resolved with confidence.

## When Formal Water Testing Is Worthwhile
- Before investing in a drip irrigation system, to check whether filtration needs will be minor or substantial based on sediment, algae, and mineral content.
- When crop performance issues (stunting, leaf burn, poor germination) are not explained by other causes and irrigation water salinity or sodium hazard is suspected.
- Before irrigating crops that will be eaten raw with water from a surface source of uncertain quality, particularly if there is any known upstream waste or contamination source.
- Periodically for a groundwater source, especially after flooding, nearby construction, or land-use changes nearby that could affect groundwater quality.
- When considering water from a new source (a newly drilled borehole, a shared communal source, or a purchased/trucked water supply) for the first time.

## Managing Water Quality Challenges
| Concern | Management Approaches |
|---|---|
| Moderate to high salinity | Select more salt-tolerant crops/varieties, improve drainage, periodically leach salts below the root zone, avoid unnecessary evaporation losses that concentrate salts |
| High sodium hazard | Apply gypsum or other calcium amendments based on soil/water testing, improve soil organic matter and structure |
| High sediment/turbidity | Install appropriate filtration (settling, sand/media, screen/disc filters depending on system), consider a settling basin before drip use |
| Elevated pH or scale-forming minerals | Monitor soil pH and amend as needed, use filtration/maintenance suited to reduce scale buildup in emitters |
| Suspected biological contamination | Avoid use on raw-eaten crops, switch to a protected source where possible, use methods that avoid wetting edible portions, extend the interval before harvest |
| Suspected chemical contamination | Avoid use until tested, identify and address the upstream source where possible, consult relevant regulatory guidance |

## Common Mistakes
- Assuming clear water is automatically safe and suitable, overlooking dissolved salts or invisible contaminants.
- Using surface water of uncertain quality directly on crops eaten raw without any treatment or testing.
- Ignoring early signs of salinity buildup (white crusting, stunted growth in patches) until yield loss is severe.
- Applying gypsum or other soil amendments to address a suspected sodium hazard without a test confirming the actual problem.
- Under-investing in filtration for drip systems fed by sediment-heavy surface water, leading to chronic clogging.
- Overlooking the interaction between soil drainage and salinity risk, applying saline water on poorly drained soils without adjusting management.

## When to Consult an Agricultural Extension Officer or Water Testing Service
- To arrange laboratory or field-kit testing for salinity (EC), sodium hazard (SAR), pH, and relevant contaminants before relying on a new or uncertain water source.
- If crop symptoms suggest a water quality problem but the cause is unclear from field observation alone.
- To interpret water test results and select suitable management responses (crop choice, amendments, filtration, leaching) for the specific farm conditions.
- Before irrigating crops destined for raw consumption with water from a source of uncertain microbial safety.
- When planning a drip irrigation system fed by a water source with known sediment, algae, or mineral content, to size filtration appropriately (see `irrigation/drip_irrigation_deep_dive.md`).
