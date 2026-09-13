# Air Quality Index (AQI) Interpretation

## Overview
The Air Quality Index (AQI) is a standardized numerical scale used by environmental agencies globally to communicate the cleanliness or pollution level of ambient air. It translates complex atmospheric concentration measurements of multiple criteria air pollutants into an intuitive indicator ranging from 0 to 500.

## Standard AQI Categories
CleanRoute AI adopts the standard United States Environmental Protection Agency (US EPA) six-tier AQI classification system:

- **0 to 50 (Good - Green):** Air quality is considered satisfactory, and air pollution poses little or no risk to the general public or sensitive individuals.
- **51 to 100 (Moderate - Yellow):** Air quality is acceptable. However, individuals with exceptional respiratory sensitivities may notice mild discomfort during prolonged outdoor physical exertion.
- **101 to 150 (Unhealthy for Sensitive Groups - Orange):** Members of sensitive groups—including children, older adults, cyclists, and individuals with respiratory conditions such as asthma—are more likely to be affected. The general public is less likely to experience noticeable symptoms.
- **151 to 200 (Unhealthy - Red):** Some members of the general public may experience adverse respiratory effects. Members of sensitive groups may experience more pronounced symptoms during prolonged outdoor travel.
- **201 to 300 (Very Unhealthy - Purple):** Health alert: Risk of increased health effects across the broader population. Outdoor exertion should be curtailed, and travelers should prioritize lower estimated exposure corridors.
- **301 to 500 (Hazardous - Maroon):** Health warning of emergency conditions: Entire population is likely to be affected. Unnecessary outdoor travel should be minimized.

## Criteria Pollutants Evaluated
The composite AQI accounts for five primary criteria pollutants:
1. Ground-level Ozone ($O_3$)
2. Fine Particulate Matter ($PM_{2.5}$)
3. Coarse Particulate Matter ($PM_{10}$)
4. Nitrogen Dioxide ($NO_2$)
5. Carbon Monoxide ($CO$) and Sulfur Dioxide ($SO_2$)

The overarching AQI for a given geographical coordinate at any hourly timestamp is determined by the pollutant exhibiting the highest individual index value (the driving or predominant pollutant).

## Role in CleanRoute AI Travel Decisions
CleanRoute AI samples atmospheric air quality along candidate journey geometries to compute an estimated route-level average AQI alongside minimum and maximum localized values. This allows travelers to evaluate route options not just on travel duration and physical distance, but also on estimated environmental air cleanliness. All AQI metrics provided are informational estimates to aid travel comparison and do not constitute medical advice or health guarantees.
