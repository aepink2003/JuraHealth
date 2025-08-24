# app.py
import streamlit as st
import requests, io, base64, re
from PIL import Image, ImageDraw
import json

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
if "gene_name" not in st.session_state:
    st.session_state.gene_name = ""
if "variant_str" not in st.session_state:
    st.session_state.variant_str = ""
if "step_idx" not in st.session_state:
    st.session_state.step_idx = 0

st.title("Gene Variant Visualizer")
gene_input = st.text_input("Enter gene (e.g., NFIX):", value=st.session_state.gene_name)
variant_input = st.text_input("Enter variant (e.g., c.240A>G):", value=st.session_state.variant_str)
run_button = st.button("Run Visualization")

if run_button:
    st.session_state.gene_name = gene_input
    st.session_state.variant_str = variant_input
    st.session_state.step_idx = 0

# --- ONLY RUN WHEN SESSION STATE HAS VALUES ---
if st.session_state.gene_name and st.session_state.variant_str:
    gene_name = st.session_state.gene_name
    variant_str = st.session_state.variant_str

    # Classify mutation
    def classify_mutation(mutation_str: str):
        mut = mutation_str.strip().lower()
        if "dup" in mut:
            return "Duplication.png"
        if "fs" in mut or "frameshift" in mut:
            if "ins" in mut: return "Frameshift-ins.GIF"
            if "del" in mut: return "Frameshift-del.GIF"
            return "Frameshift-del.GIF"
        if re.search(r"del", mut) and "fs" not in mut:
            return "Frameshift-del.GIF"
        if re.search(r"ins", mut) and "fs" not in mut:
            return "Frameshift-ins.GIF"
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

    captions = {
    "8bitChrom.png": "Here are all 23 pairs of human chromosomes. Your gene is on the highlighted one.",
    "p arm q arm labeled.PNG": "Each chromosome has two parts: the p arm (short, on top) and the q arm (long, on bottom).",
    "Just p arm.PNG": "We’re zooming in on the p arm of your chromosome — this is where your gene is located.",
    "Just q arm.PNG": "We’re zooming in on the q arm of your chromosome — this is where your gene is located.",
    "dna p arm.PNG": "Chromosomes are made of DNA. Here’s a closer look at the p arm where your gene lives.",
    "dna q arm.PNG": "Chromosomes are made of DNA. Here’s a closer look at the q arm where your gene lives.",
    "Frameshift-ins.GIF": "An insertion adds extra DNA letters. This shifts how the code is read, which can change the whole protein after this point.",
    "Frameshift-del.GIF": "A deletion removes DNA letters. This shifts how the code is read, which can scramble the protein after this point.",
    "Missense.png": "A missense change swaps one DNA letter for another, which can change one building block in the protein.",
    "Nonsense.png": "A nonsense change tells the protein to stop too early. This can make the protein much shorter and not work properly.",
    "Duplication.png": "A duplication copies part of the DNA. This can make the protein too long or change how it works."
}

    # --- NAVIGATION STATE ---
    if "step_idx" not in st.session_state:
        st.session_state.step_idx = 0

    frames = [
    ("8bitChrom.png", step0_b64),
    ("p arm q arm labeled.PNG", step1_b64),
    (arm_file, step2_b64),
    (f"dna {arm} arm.PNG", step3_b64),
    (classify_mutation(variant_str), step4_b64)
]

    captions_list = [captions[fname] for fname, _ in frames]
    frame_data = [f"data:image/png;base64,{b64}" for _, b64 in frames]
    
    # --- DISPLAY WITH CLICKABLE IMAGE AND NAVIGATION BUTTONS ---
    html = f"""
    <div style="font-family: sans-serif; color:black; text-align:center;">
        <div><strong>Gene:</strong> {gene_name} &nbsp;|&nbsp; <strong>Chromosome number:</strong> {chromosome_num} &nbsp;|&nbsp; <strong>Chromosome arm:</strong> {arm} &nbsp;|&nbsp; <strong>Variant:</strong> {variant_str}</div>

        <div style="margin-top:12px;">
            <button id="backBtn" style="background-color:#7B2CBF; color:white; border:none; border-radius:8px; padding:0.5em 1em; margin-right:1em; cursor:pointer;">&lt;-- Back</button>
            <button id="nextBtn" style="background-color:#7B2CBF; color:white; border:none; border-radius:8px; padding:0.5em 1em; margin-left:1em; cursor:pointer;">Next --&gt;</button>
        </div>

        <div id="caption" style="margin-top:8px; font-size:1.1em;">
            {captions_list[st.session_state.step_idx]}
        </div>
        <img id="walkthrough" 
            src="{frame_data[st.session_state.step_idx]}" 
            style="cursor:pointer; border:3px solid #7B2CBF; border-radius:12px; width:500px; height:400px ; object-fit:contain;" />
    <script>
        const frames = {json.dumps(frame_data)};
        const captions = {json.dumps(captions_list)};
        let idx = {st.session_state.step_idx};

        const img = document.getElementById("walkthrough");
        const cap = document.getElementById("caption");
        const backBtn = document.getElementById("backBtn");
        const nextBtn = document.getElementById("nextBtn");

        img.addEventListener("click", () => {{
            if (idx < frames.length - 1) {{
                idx++;
                img.src = frames[idx];
                cap.textContent = captions[idx];
            }}
        }});

        backBtn.addEventListener("click", () => {{
            if (idx > 0) {{
                idx--;
                img.src = frames[idx];
                cap.textContent = captions[idx];
            }}
        }});

        nextBtn.addEventListener("click", () => {{
            if (idx < frames.length - 1) {{
                idx++;
                img.src = frames[idx];
                cap.textContent = captions[idx];
            }}
        }});
    </script>
    </div>
    """
    st.components.v1.html(html, height=900)

    # --- GALLERY VIEW ---
    gallery_html = f"""
<div style="margin-top:30px; text-align:center;">
    <h3>Step Gallery</h3>
    <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap;">
"""
    for i, (fname, b64) in enumerate(frames):
        gallery_html += f"""
        <div style="text-align:center; cursor:pointer;" onclick="updateStep({i})">
            <img src="data:image/png;base64,{b64}" 
                 style="width:120px; height:100px; object-fit:contain; border:2px solid #7B2CBF; border-radius:8px;"/>
            <div style="margin-top:4px;">Step {i+1}</div>
        </div>
    """
    gallery_html += """
    </div>
</div>
<script>
function updateStep(i) {
    const frames = %s;
    const captions = %s;
    const img = document.getElementById("walkthrough");
    const cap = document.getElementById("caption");
    img.src = frames[i];
    cap.textContent = captions[i];
}
</script>
""" % (json.dumps(frame_data), json.dumps(captions_list))

    st.components.v1.html(gallery_html, height=350)

    # --- CSS BUTTON STYLE ---
    st.markdown("""
    <style>
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