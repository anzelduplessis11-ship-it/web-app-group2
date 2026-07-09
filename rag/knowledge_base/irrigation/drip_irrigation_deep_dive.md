# Drip Irrigation Deep Dive: System Design, Installation, and Maintenance

## Overview
Drip (trickle) irrigation applies water slowly and directly to the plant root zone through a network of pipes, tubing, and emitters, minimizing losses to evaporation, runoff, and deep percolation. For a general comparison of irrigation methods, see `irrigation/irrigation_methods.md`; for deciding when and how much to irrigate once a drip system is installed, see `irrigation/irrigation_scheduling.md`. This document focuses specifically on how to design, install, and maintain a drip system appropriate for smallholder budgets and conditions, including low-cost bucket-kit and gravity-fed options.

## Why Choose Drip Irrigation
- Water use efficiency is typically 80-95%, well above surface irrigation (40-60%) and sprinkler irrigation (70-85%), because water is delivered close to the root and little wets the soil surface between rows.
- Reduces weed pressure between rows since only the crop line is wetted, lowering weeding labour.
- Keeps foliage dry, reducing the risk of many fungal and bacterial diseases that spread through leaf wetness (see individual crop and disease documents in `crops/` and `diseases/`).
- Allows fertilizer to be applied through the system (fertigation), improving nutrient use efficiency when done carefully.
- Well suited to high-value crops such as tomato, pepper, onion, and orchard/fruit crops where the investment can be recovered through improved yield and quality.
- Works on uneven or sloped terrain better than surface irrigation, and can be adapted to very small plots as well as larger fields.

## Core System Components
A drip system generally consists of the following components, moving from the water source to the plant:

| Component | Function |
|---|---|
| Water source | Borehole, well, tank, pond, or piped supply; must provide adequate flow and pressure |
| Pump (if needed) | Provides pressure where gravity head is insufficient; can be powered by diesel, electricity, or solar |
| Filter | Removes sediment, algae, and debris before water reaches emitters; essential for preventing clogging |
| Pressure regulator | Maintains even pressure across the system, especially important on sloped or long fields |
| Main line | Larger-diameter pipe carrying water from the source to the field |
| Submain/manifold lines | Distribute water from the main line to individual driplines |
| Driplines (laterals) | Tubing laid along crop rows, fitted with emitters or drip tape |
| Emitters | Small devices (or built-in perforations in drip tape) that release water at a controlled, low flow rate |
| Valves | Control water flow to different sections or zones of the field |

## Types of Drip Systems for Smallholders
### Drip Tape
- Thin-walled tubing with pre-formed emitter perforations at fixed spacing, typically used for row crops and seasonal vegetables.
- Lower cost per unit length than rigid dripline with individual emitters, but less durable and usually replaced after one or a few seasons.
- Good option for annual vegetable crops where row spacing is consistent from season to season.

### Rigid Dripline with Point-Source Emitters
- Thicker-walled tubing fitted with individual emitters (button drippers or in-line emitters) at chosen spacing.
- More durable and reusable across multiple seasons, better suited to perennial crops such as fruit trees where emitter spacing must match plant spacing rather than uniform row spacing.
- Higher upfront cost per unit length than drip tape but lower replacement frequency.

### Gravity-Fed Bucket or Drum Kits
- A raised bucket, drum, or tank feeds a small network of tubing by gravity head alone, without a pump.
- Suitable for very small plots (kitchen gardens, nurseries, small vegetable beds) where pumping is not affordable or where no electricity/fuel is available.
- Requires the reservoir to be elevated enough (typically at least 1-1.5 metres above the field) to generate sufficient pressure for even flow.
- Flow is limited and coverage area is small compared to pumped systems, but the low cost and simplicity make it a practical entry point for smallholders.

### Pumped Pressurized Systems
- Use a pump (diesel, electric, or solar-powered) to pressurize the system, allowing larger areas, longer dripline runs, and more consistent pressure regardless of terrain.
- Solar-powered pumps are increasingly used where grid electricity is unavailable or unreliable, though initial investment is a consideration.
- Appropriate for larger plots or where the water source is not elevated relative to the field.

## Designing a Drip System
1. **Assess the water source**: confirm adequate flow rate and, where relevant, acceptable water quality (see `irrigation/irrigation_water_quality.md`) to avoid excessive emitter clogging from sediment, algae, or dissolved minerals.
2. **Map the field and crop layout**: note row spacing, plant spacing, field length, and slope, since these determine dripline length, emitter spacing, and the number of zones needed.
3. **Select emitter type and spacing** to match crop root spread: closely spaced emitters or continuous drip tape for closely planted vegetables; wider point-source emitter spacing for trees and widely spaced perennials.
4. **Calculate flow and pressure requirements**: total emitter flow rate across a zone must be within the capacity of the water source and pump; pressure must be sufficient to reach the far end of each dripline at an even rate.
5. **Plan filtration** appropriate to the water source: sand or media filters for surface water with algae and organic debris; screen or disc filters for borehole water with fine sediment.
6. **Divide large areas into irrigation zones** so that each zone's water demand matches available flow and pressure, and so that different crops or growth stages can be watered independently.
7. **Plan for future maintenance access**: valves, flush points, and filters should be placed where they can be reached and serviced without disturbing crops.

## Installation Steps
1. Lay out and connect the main line from the water source to the field edge, burying it where it crosses walkways or vehicle paths to prevent damage.
2. Install the filter and pressure regulator between the pump/source and the main line, before water reaches the submains.
3. Connect submain lines to the main line at the field edge, running them along the head of each set of crop rows.
4. Attach driplines (drip tape or dripline with emitters) to the submains, laying them along crop rows at the planned spacing.
5. Flush the system thoroughly before capping the ends of driplines, to clear out any dirt or debris introduced during installation.
6. Check for even water emergence along each line once pressurized; adjust or replace any emitters showing no flow or excessive flow.
7. Secure driplines against wind and disturbance using stakes or light soil cover at intervals, while keeping emitters accessible for inspection.

## Operating a Drip System
- Run the system long enough to wet the full target root depth, then allow the soil to draw down before the next irrigation, following the same principles as in `irrigation/irrigation_scheduling.md`.
- Because drip wets a smaller soil volume than surface or sprinkler irrigation, irrigation frequency is often higher but each application uses less water; monitor soil moisture at root depth rather than relying on a fixed schedule.
- Fertigation (injecting soluble fertilizer into the irrigation water) can improve nutrient timing and uptake, but requires a functioning injector and should never introduce fertilizer upstream of the filter unless the filter is designed to handle it, to avoid contaminating the filtration system.
- Inspect the system visually at each irrigation for leaks, blocked emitters (indicated by dry spots), or uneven wetting patterns.

## Maintenance and Troubleshooting
### Routine Maintenance
- Clean or backwash filters regularly, with frequency depending on water quality; sediment-laden or algae-prone sources need more frequent cleaning.
- Flush the ends of main lines, submains, and driplines periodically by opening end caps to release accumulated sediment.
- Check emitters periodically for clogging, and clear or replace clogged units.
- Inspect tubing for damage from rodents, cracking from sun exposure (UV degradation), or accidental cuts from tools, repairing promptly with couplers or replacement sections.
- Store above-ground gravity-kit reservoirs covered to reduce algae growth and debris entry.

### Common Problems and Causes
| Problem | Likely Cause | Response |
|---|---|---|
| Uneven flow across the field | Pressure loss over long lines, or partial clogging | Add pressure regulation, shorten zones, flush and clean filters/emitters |
| Emitters not releasing water | Clogging from sediment, algae, or mineral (scale) buildup | Clean or replace emitters; improve filtration; consider water treatment if scale is chronic |
| Dry patches despite normal system pressure | Localized emitter blockage or a kinked/damaged line | Inspect and clear the affected section; replace damaged tubing |
| Water pooling at the surface | Emitter flow rate exceeds soil infiltration rate, or leaks | Choose lower flow-rate emitters for slow-infiltration soils; repair leaks |
| Rapid emitter clogging | Poor water quality (high sediment, algae, or dissolved minerals) | Test and improve water quality; upgrade filtration (see `irrigation/irrigation_water_quality.md`) |
| Rodent or pest damage to tubing | Exposed tubing attractive to rodents, especially where water pools | Bury or cover vulnerable sections; repair promptly to limit water loss |

## Extending the Life of a Drip System
- Protect tubing from direct sun exposure where practical, since UV exposure accelerates plastic degradation over time.
- Drain and store removable components (tape, fittings) during the off-season if the field will be fallow, reducing exposure to weather and pests.
- Keep a small stock of spare emitters, connectors, and end caps on hand, since minor repairs are frequent and delays reduce irrigation uniformity.
- Match system capacity to the water source realistically; overloading a small water source with a system sized for a larger area causes chronic pressure and flow problems.

## Common Mistakes
- Skipping filtration or under-sizing the filter, leading to frequent emitter clogging and uneven irrigation.
- Failing to flush lines before capping them during installation, leaving debris to clog emitters later.
- Sizing zones larger than the water source and pump can support, causing weak flow and pressure at the far end of driplines.
- Leaving leaks or damaged tubing unrepaired, which wastes water and can create waterlogged patches that encourage disease and weeds.
- Ignoring water quality until clogging becomes severe, rather than testing and filtering proactively.
- Treating a gravity-fed kit as suitable for areas far larger than its limited flow and pressure can actually cover evenly.

## When to Consult an Agricultural Extension Officer or Irrigation Specialist
- Before selecting and sizing a drip system, to match emitter type, spacing, and zone size to the specific water source, crop, and field layout.
- If recurring clogging or uneven flow persists despite routine filter cleaning and flushing.
- To assess whether water quality (sediment, algae, salinity, or mineral content) requires additional treatment or a different filtration approach; see `irrigation/irrigation_water_quality.md`.
- When considering fertigation, to plan safe injection rates and equipment compatible with the crop and system.
- Before scaling up from a small pilot area to a full field, to confirm the water source and pump can reliably support the larger system.
