# Gene Variant Visualizer 🧬

## Overview
The **Gene Variant Visualizer** is a Streamlit web app that helps users visualize the location of a genetic variant within human chromosomes and understand its context.  
It uses the [Ensembl REST API](https://rest.ensembl.org/) to fetch gene and chromosome data, determines whether the variant is on the p arm or q arm, and walks the user through an interactive step-by-step image sequence.

---

## Features
- **Gene & Variant Input** – Enter a gene symbol (e.g., `NFIX`) and a variant (e.g., `c.240A>G`).
- **Live Ensembl API Integration** – Retrieves chromosome number and variant position automatically.
- **Interactive Walkthrough** – Step through 5 educational images explaining:
  1. Which chromosome the variant is on
  2. Chromosome arms (p & q)
  3. Focus on the correct arm
  4. DNA structure at that arm
  5. Example of the variant type
- **Dual Navigation** –  
  - Click on the image to go to the next step  
  - Use Back/Next buttons for manual navigation
- **Custom Styling** – Purple-accent theme, white background, clean layout.

---

## How It Works
1. **Input**  
   - Type a valid **gene symbol** (e.g., `NFIX`)  
   - Type the **variant notation** (e.g., `c.240A>G`)

2. **Processing**  
   - The app queries Ensembl’s API to find the chromosome and position.
   - Determines if the variant is on the **p** or **q** arm.
   - Classifies the mutation type (e.g., missense, nonsense, frameshift, duplication).

3. **Visualization**  
   - Displays an image walkthrough with captions explaining each step.
   - Navigation can be done by clicking the image or using Back/Next buttons.

---

## Requirements
Install dependencies:
```bash
pip install streamlit requests pillow
