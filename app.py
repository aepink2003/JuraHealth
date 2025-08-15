# app.py
import streamlit as st
import requests, io, base64, re
from PIL import Image, ImageDraw

# --- PAGE CONFIG ---
st.set_page_config(page_title="Gene Variant Visualizer", page_icon="🧬", layout="centered")
st.markdown("""
<style>
    body {
        background-color: white;
        color: white;
    }
    .stButton>button {
        background-color: #7B2CBF;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
        border: none;
    }
    .stButton>button:hover {
        background-color: #9D4EDD;
    }
</style>
""", unsafe_allow_html=True)

# --- INPUT FORM ---
st.title("Gene Variant Visualizer")
gene_name = st.text_input("Enter gene (e.g., NFIX):")
variant_str = st.text_input("Enter variant (e.g., c.240A>G):")
run_button = st.button("Run Visualization")

# --- ONLY RUN WHEN BUTTON CLICKED ---
if run_button and gene_name and variant_str:

    # Classify mutation
    def classify_mutation(mutation_str: str):
        mut = mutation_str.strip().lower()
        if "dup" in mut:
            return "Duplication.png"
        if "fs" in mut or "frameshift" in mut:
            if "ins" in mut: return "Frameshift-ins.png"
            if "del" in mut: return "Frameshift-del.png"
            return "Frameshift-del.png"
        if re.search(r"del", mut) and "fs" not in mut:
            return "Frameshift-del.png"
        if re.search(r"ins", mut) and "fs" not in mut:
            return "Frameshift-ins.png"
        if "*" in mut or "ter" in mut or re.search(r"[a-z]{3}\d+x", mut):
            return "Nonsense.png"
        if ">" in mut or re.search(r"[a-z]{3}\d+[a-z]{3}", mut):
            return "Missense.png"
        return "Missense.png"

    # Ensembl info
    def get_gene_info(gene_symbol):
        xref = f"https://rest.ensembl.org/xrefs/symbol/homo_sapiens/{gene_symbol}?content-type=application/json"
        r = requests.get(xref)
        if not r.ok or not r.json():
            return None, None, None
        ensembl_id = r.json()[0]["id"]
        lookup = f"https://rest.ensembl.org/lookup/id/{ensembl_id}?content-type=application/json"
        lr = requests.get(lookup)
        if not lr.ok or not lr.json():
            return None, None, None
        data = lr.json()
        chrom = data.get("seq_region_name")
        start = data.get("start")
        return chrom, ensembl_id, start

    chromosome_num, ensembl_id, variant_start = get_gene_info(gene_name)
    if not chromosome_num:
        st.error("Gene not found in Ensembl (check symbol).")
        st.stop()

    asm = f"https://rest.ensembl.org/info/assembly/homo_sapiens/{chromosome_num}?content-type=application/json"
    asm_r = requests.get(asm)
    asm_json = asm_r.json()
    chromosome_length = asm_json["length"]
    arm = "p" if (variant_start and variant_start < (chromosome_length/2)) else "q"

    # Draw red box on correct chromosome
    img = Image.open("8bitChrom.png").convert("RGBA")
    chrom_width, chrom_height = 45, 105
    left_margin, top_margin = 44, 43
    horizontal_spacing, vertical_spacing = 30, 45
    cols_per_row = 8

    chrom_coords = {}
    cnum = 1
    for row in range(3):
        y1 = top_margin + row * (chrom_height + vertical_spacing)
        for col in range(cols_per_row):
            if cnum > 23: break
            x1 = left_margin + col * (chrom_width + horizontal_spacing)
            chrom_coords[str(cnum)] = (x1, y1, x1 + chrom_width, y1 + chrom_height)
            cnum += 1
    if str(chromosome_num) in chrom_coords:
        draw = ImageDraw.Draw(img)
        draw.rectangle(chrom_coords[str(chromosome_num)], outline="red", width=6)

    def pil_to_b64(pil_img):
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def file_to_b64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    step0_b64 = pil_to_b64(img)
    step1_b64 = file_to_b64("p arm q arm labeled.PNG")
    arm_file = "Just p arm.PNG" if arm == "p" else "Just q arm.PNG"
    step2_b64 = file_to_b64(arm_file)
    dna_file = f"dna {arm} arm.PNG"
    step3_b64 = file_to_b64(dna_file)
    step4_b64 = file_to_b64(classify_mutation(variant_str))

    captions = [
        "These are all 23 chromosomes, your variant is located on the highlighted chromosome.\n Click on the highlighted box to learn more!",
        "This diagram explains the p arm (short) and q arm (long).",
        "This is the arm of the chromosome we will be focusing on.",
        "Chromosomes are long strands of DNA tightly packed into structures.",
        "Example of this mutation type."
    ]

    html = f"""
    <div style="font-family: sans-serif; color:black">
      <div><strong>Gene:</strong> {gene_name} &nbsp;|&nbsp; <strong>Chr:</strong> {chromosome_num}{arm} &nbsp;|&nbsp; <strong>Variant:</strong> {variant_str}</div>
      <div style="margin-bottom:8px;">Click the image to step through →</div>
    <img id="walkthrough" src="data:image/png;base64,{step0_b64}" 
     style="cursor:pointer; border:3px solid #7B2CBF; border-radius:12px; width:100%; max-width:800px; height:auto;" />      <div id="caption" style="margin-top:8px;">{captions[0]}</div>
      <script>
      (function() {{
        const img = document.getElementById('walkthrough');
        const cap = document.getElementById('caption');
        const frames = [
            "data:image/png;base64,{step0_b64}",
            "data:image/png;base64,{step1_b64}",
            "data:image/png;base64,{step2_b64}",
            "data:image/png;base64,{step3_b64}",
            "data:image/png;base64,{step4_b64}"
        ];
        const captions = {captions};
        let idx = 0;
        img.addEventListener('click', () => {{
            idx = Math.min(idx + 1, frames.length - 1);
            img.src = frames[idx];
            cap.textContent = captions[idx];
        }});
      }})();
      </script>
    </div>
    """
    st.components.v1.html(html, height=900)