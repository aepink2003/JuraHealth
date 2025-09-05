# app.py
import streamlit as st
import requests, io, base64, re
import os
from PIL import Image, ImageDraw
import json
import openai

# openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- PAGE CONFIG ---
st.set_page_config(page_title="Gene Variant Visualizer", page_icon="🧬", layout="centered")
# --- Responsive meta viewport and responsive styles ---
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1">
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
    /* Responsive disclaimer box */
    .disclaimer-box {
        background-color: #FFCCCC;
        border: 6px solid red;
        padding: 12px;
        border-radius: 8px;
        font-size: 1.1em;
        color: black;
        margin: 16px 0;
        box-sizing: border-box;
        max-width: 100%;
    }
    /* Responsive walkthrough container and images */
    #walkthrough_container, #ideo-container, #walkthrough {
        width: 100%;
        max-width: 500px;
        height: auto;
        aspect-ratio: 5/4;
        margin: auto;
        display: flex;
        justify-content: center;
        align-items: center;
        box-sizing: border-box;
    }
    #walkthrough {
        max-width: 100%;
        height: auto;
        object-fit: contain;
    }
    #ideo-container {
        max-width: 100%;
        height: auto;
        min-height: 200px;
    }
    /* Responsive gallery images */
    .step-gallery-img, .gallery-thumb img {
        width: 100%;
        max-width: 200px;
        height: auto;
        object-fit: contain;
    }
    @media (max-width: 600px) {
        #walkthrough_container, #ideo-container {
            max-width: 98vw;
            min-width: 0;
        }
        #walkthrough {
            max-width: 98vw;
        }
        .stButton>button {
            width: 100%;
            min-width: 0;
            box-sizing: border-box;
        }
    }
</style>
""", unsafe_allow_html=True)
import random

# --- FUN FACTS ---
fun_facts = [
    "All ~30,000 of your genes are tucked inside these 23 pairs of chromosomes.",
    "If you stretched out all of the DNA in one of your cells, it would be about 6.5 feet long!",
    "A chromosome is made up of two identical sister chromatids — the left and right halves.",
    "Your body has around 37 trillion cells, and almost every one carries a full set of DNA.",
    "Only ~2% of your DNA actually codes for proteins — the rest helps regulate and organize your genome.",
    "Mitochondria have their own DNA, passed down from your mother!",
    "The human Y chromosome is much smaller than the X chromosome — it carries fewer genes."
]

if "show_intro" not in st.session_state:
    st.session_state.show_intro = True

# --- DISCLAIMER BOX ---
st.markdown("""
<div class="disclaimer-box">
    <strong>Disclaimer:</strong> This page is still under construction. Always consult with a licensed professional for medical or genetic questions.
</div>
""", unsafe_allow_html=True)

if st.session_state.show_intro:
    st.title(" Welcome to the Gene Variant Visualizer")

    

    st.markdown("""
    This tool was designed to make understanding your genetic variant easier.  
    It walks you step-by-step from your chromosome, to the DNA sequence,  
    and finally to what your specific variant means.  
    """)
    
    fact = random.choice(fun_facts)
    st.markdown(f"""
    <div style="background-color:#F3F0FF; padding:12px; border-radius:8px; font-size:1.1em; color:black; margin:16px 0;">
        <strong>Did you know?</strong> {fact}
    </div>
    """, unsafe_allow_html=True)

    if st.button("Start Visualization"):
        st.session_state.show_intro = False
        st.rerun()
    st.stop()

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

    # --- IDEOGRAM STANDALONE VIEW ---
    ideo_start = max(1, int(variant_start) - 100000) if variant_start else 1
    ideo_stop = (int(variant_start) + 100000) if variant_start else 200000

    # --- REMOVED IDEOGRAM STANDALONE VIEW ---

    step1_b64 = file_to_b64("p arm q arm labeled.PNG")
    arm_file = "Just p arm.PNG" if arm == "p" else "Just q arm.PNG"
    step2_b64 = file_to_b64(arm_file)
    dna_file = f"dna {arm} arm.PNG"
    step3_b64 = file_to_b64(dna_file)
    step4_b64 = file_to_b64(classify_mutation(variant_str))

    captions = {
        "8bitChrom.png": "Here are all 23 pairs of human chromosomes. Your gene is on the highlighted one.",
        "IDEO_BLOCK": "Earlier, we showed the chromosome in a simplified way, with the p arm on top and the q arm on the bottom. Scientists usually show the chromosome as one vertical shape, with light and dark stripes called bands. These bands help pinpoint exactly where a gene is. That’s the view you see here. {gene_name}'s location is marked below",
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
        ("IDEO_BLOCK", None),
        (classify_mutation(variant_str), step4_b64)
        
    ]

    captions_list = [captions[fname] for fname, _ in frames]
    frame_data = []
    for fname, data in frames:
        if fname == "IDEO_BLOCK":
            frame_data.append("IDEO_BLOCK")
        else:
            frame_data.append(f"data:image/png;base64,{data}")
    
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
        <div id="walkthrough_container" style="cursor:pointer; border:3px solid #7B2CBF; border-radius:12px; max-width:500px; width:100%; margin:auto; display:flex; justify-content:center; align-items:center; aspect-ratio:5/4;">
"""

    # Insert static ideogram container (always present, but hidden unless IDEO_BLOCK step)
    html += f"""
    <div id="ideo-container" style="max-width:500px; width:100%; aspect-ratio:5/4; display:none;"></div>
    <img id="walkthrough" style="max-width:100%; width:100%; height:auto; object-fit:contain; display:none;" />
    <script src="https://cdn.jsdelivr.net/npm/ideogram/dist/js/ideogram.min.js"></script>
    <script>
    if (!window.myIdeogram) {{
        window.myIdeogram = new Ideogram({{
            organism: 'human',
            container: '#ideo-container',
            chromosomes: ["{chromosome_num}"],
            resolution: 550,
            chrHeight: 300,
            chrMargin: 20,
            chrLabelSize: 18,
            showChromosomeLabels: true,
            annotationHeight: 6,
            annotations: [{{
                name: "{gene_name}",
                chr: "{chromosome_num}",
                start: {ideo_start},
                stop: {ideo_stop}
            }}]
        }});
    }}
    </script>

""" % (chromosome_num, gene_name, chromosome_num, ideo_start, ideo_stop)

    html += """
        </div>
    <script>
        const frames = """ + json.dumps(frame_data) + """;
        const captions = """ + json.dumps(captions_list) + """;
        let idx = """ + str(st.session_state.step_idx) + """;

        const container = document.getElementById("walkthrough_container");
        const cap = document.getElementById("caption");
        const backBtn = document.getElementById("backBtn");
        const nextBtn = document.getElementById("nextBtn");
        const ideoDiv = document.getElementById("ideo-container");
        const walkthroughImg = document.getElementById("walkthrough");

        function renderFrame(i) {
            const frame = frames[i];
            cap.textContent = captions[i];
            if (frame === "IDEO_BLOCK") {
                ideoDiv.style.display = 'block';
                walkthroughImg.style.display = 'none';
            } else {
                ideoDiv.style.display = 'none';
                walkthroughImg.style.display = 'block';
                walkthroughImg.src = frame;
            }
        }

        // Initial render
        renderFrame(idx);

        backBtn.addEventListener("click", () => {
            if (idx > 0) {
                idx--;
                renderFrame(idx);
            }
        });

        nextBtn.addEventListener("click", () => {
            if (idx < frames.length - 1) {
                idx++;
                renderFrame(idx);
            }
        });

        container.addEventListener("click", () => {
            if (idx < frames.length - 1) {
                idx++;
                renderFrame(idx);
            }
        });
    </script>
    </div>
    """

    # --- GALLERY VIEW ---
    gallery_html = f"""
<div style="padding-top:0; text-align:center;">
    <h3 style="margin:4px 0; padding:0;">Step Gallery</h3>
    <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap; margin-top:0; padding-top:0;">
    """
    for i, (fname, data) in enumerate(frames):
        if fname == "IDEO_BLOCK":
            thumb = "<div style='width:100%; max-width:200px; aspect-ratio:1/1; display:flex; align-items:center; justify-content:center; background:#F3F0FF; color:#7B2CBF; font-weight:bold; border:2px solid #7B2CBF; border-radius:8px;'>Ideogram</div>"
        else:
            thumb = f"<img src='data:image/png;base64,{data}' style='width:100%; max-width:200px; height:auto; object-fit:contain; border:2px solid #7B2CBF; border-radius:8px;'/>"
        gallery_html += f"""
        <div class="gallery-thumb" style="text-align:center; cursor:pointer; max-width:200px;" onclick="updateStep({i})">
            {thumb}
            <div style="margin-top:4px;">Step {i+1}</div>
        </div>
    """
    gallery_html += f"""
    </div>
</div>
<script>
function updateStep(i) {{
    idx = i;
    renderFrame(idx);
}}
</script>
"""

    combined_html = html + gallery_html

    st.components.v1.html(combined_html, height=1200)

    # --- CSS BUTTON STYLE ---
# Already included responsive button style above, omit duplicate.


# import openai  # Uncomment when switching to OpenAI

# ============================================================
# CONFIGURATION
# ============================================================


# chat bot func


from openai import OpenAI
import os

def query_openai(prompt):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, "OpenAI API key not found. Please set OPENAI_API_KEY."

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert geneticist explaining variants and genes simply "
                        "and clearly as if you were talking to a middle schooler. "
                        "ALWAYS INCLUDE A DISCLAIMER THAT YOU ARE AN AI AND INFORMATION MAY BE INACCURATE."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, f"Error calling OpenAI API: {str(e)}"

# --- CHAT UI ---

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_message = st.chat_input("Ask me about your gene or variant...")

if user_message:
    # Save user message
    st.session_state.chat_history.append({"role": "user", "content": user_message})

    # context from app: gene & variant info
    context = ""
    if "gene_name" in st.session_state:
        context += f"Gene: {st.session_state.gene_name}\n"
    if "variant_str" in st.session_state:
        context += f"Variant: {st.session_state.variant_str}\n"

    full_prompt = f"{context}\nUser Question: {user_message}" if context else user_message

    # Call OpenAI
    with st.spinner("Thinking..."):
        bot_reply, error = query_openai(full_prompt)

    # If there's an error (e.g., missing key)
    if error:
        st.error(error)
    else:
        # Save bot reply
        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})

# Display the chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])