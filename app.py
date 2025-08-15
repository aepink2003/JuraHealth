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
        "These are all 23 chromosomes, your variant is located on the highlighted chromosome. Click on the highlighted box to learn more!",
        "This diagram explains the p arm (short and on top) and q arm (long and on the bottom).",
        "This is the arm of the chromosome we will be focusing on. This is also written above this diagram.",
        "Chromosomes are long strands of DNA tightly packed into structures. The variations that effect genes happen in the sequences of DNA. ",
        "Example of this variation type. The top strand represents the 'original' - the one below shows the change and how it affects the DNA sequence and how its read."
    ]

    # --- NAVIGATION STATE ---
    if "step_idx" not in st.session_state:
        st.session_state.step_idx = 0

    frames = [
    f"data:image/png;base64,{step0_b64}",
    f"data:image/png;base64,{step1_b64}",
    f"data:image/png;base64,{step2_b64}",
    f"data:image/png;base64,{step3_b64}",
    f"data:image/png;base64,{step4_b64}"
    ]
    captions_list = captions

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("<-- Back") and st.session_state.step_idx > 0:
            st.session_state.step_idx -= 1
            st.rerun()
    with col3:
        if st.button("Next -->") and st.session_state.step_idx < len(frames) - 1:
            st.session_state.step_idx += 1
            st.rerun()

    st.markdown(f"<div style='font-family: sans-serif; color:black; text-align:center; margin-bottom:10px;'><strong>Gene:</strong> {gene_name} &nbsp;|&nbsp; <strong>Chr:</strong> {chromosome_num}{arm} &nbsp;|&nbsp; <strong>Variant:</strong> {variant_str}</div>", unsafe_allow_html=True)

    # Make the image clickable using JavaScript in st.components.v1.html
    import streamlit.components.v1 as components
    # Prepare arrays for JS
    js_frames = frames
    js_captions = captions_list
    idx = st.session_state.step_idx
    max_idx = len(frames) - 1
    # The component will post a message to Streamlit when the image is clicked
    # and Streamlit will increase the step index.
    # We use window.parent.postMessage to communicate with Streamlit.
    components.html(f"""
        <div style="text-align:center;">
            <img id="step-img" src="{js_frames[idx]}" alt="step image" style="width:100%;max-width:500px;cursor:pointer;border-radius:8px;box-shadow:0 2px 16px #0001;" onclick="document.getElementById('caption').innerText = captions[Math.min(currentIdx+1, {max_idx})]; window.parent.postMessage({{isStreamlitMessage: true, type: 'step_image_click'}}, '*');"/>
            <div id="caption" style="margin-top:1em;font-size:1.1em;color:#222;">{js_captions[idx]}</div>
        </div>
        <script>
        var currentIdx = {idx};
        var maxIdx = {max_idx};
        var captions = {json.dumps(js_captions)};
        // Listen for rerun to update image/caption
        window.addEventListener('message', function(e) {{
            if (e.data && e.data.type === 'streamlit:setComponentValue') {{
                currentIdx = e.data.value;
                document.getElementById('step-img').src = {json.dumps(js_frames)}[currentIdx];
                document.getElementById('caption').innerText = captions[currentIdx];
            }}
        }});
        </script>
    """, height=420)

    import streamlit as __st
    image_clicked = __st.experimental_get_query_params().get("clicked", [None])[0]
   
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