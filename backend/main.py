import os
import sys
import re
import string
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from urllib.parse import urlparse
from tld import get_tld
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Model Libraries
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier
from transformers import BertTokenizer, BertModel
from tranco import Tranco

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"Working Directory: {BASE_DIR}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. MODEL ARCHITECTURES
# ==========================================

# URLNet
all_chars = string.printable
char2idx = {c: i + 1 for i, c in enumerate(all_chars)}

class SimpleURLNet(nn.Module):
    def __init__(self, vocab_size=len(char2idx)+1, embed_dim=32, num_classes=4):
        super(SimpleURLNet, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.conv1 = nn.Conv1d(embed_dim, 64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = self.pool(x).squeeze(-1)
        x = self.fc(x)
        return x

# BERT
class BertURLClassifier(nn.Module):
    def __init__(self, num_classes=4):
        super().__init__()
        self.bert = BertModel.from_pretrained("bert-base-uncased")
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(768, num_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        cls_token = outputs.last_hidden_state[:, 0, :]
        x = self.dropout(cls_token)
        return self.fc(x)

# ==========================================
# 2. LOAD RESOURCES
# ==========================================

# Tranco Whitelist
print("Loading whitelist database...")
try:
    t = Tranco(cache=True, scope='list')
    tranco_list = t.list()
    print("Tranco list loaded.")
except:
    tranco_list = None
    print("Tranco list failed.")

# Models
print("Loading AI models...")
try:
    lgbm_model = lgb.Booster(model_file=os.path.join(BASE_DIR, 'lgbm_model_weightedclass.txt'))
    print("LightGBM loaded.")
except: lgbm_model = None

try:
    xgb_model = xgb.Booster()
    xgb_model.load_model(os.path.join(BASE_DIR, 'xgboostsmote_model.json'))
    print("XGBoost loaded.")
except: xgb_model = None

try:
    cat_model = CatBoostClassifier()
    cat_model.load_model(os.path.join(BASE_DIR, 'catboost_modelweighted.cbm'))
    print("CatBoost loaded.")
except: cat_model = None

try:
    urlnet_model = SimpleURLNet()
    path = os.path.join(BASE_DIR, 'urlnetWL.pth')
    state = torch.load(path, map_location='cpu')
    urlnet_model.load_state_dict(state if isinstance(state, dict) else state)
    urlnet_model.eval()
    print("URLNet loaded.")
except: urlnet_model = None

try:
    bert_path = os.path.join(BASE_DIR, "bert_url_model")
    if os.path.exists(bert_path):
        bert_tokenizer = BertTokenizer.from_pretrained(bert_path)
        bert_model = BertURLClassifier(num_classes=4)
        bert_model.load_state_dict(torch.load(os.path.join(bert_path, "model.pt"), map_location='cpu'))
        bert_model.eval()
        print("BERT loaded.")
    else: bert_model = None
except: bert_model = None

# ==========================================
# 3. FEATURES
# ==========================================
FEATURE_NAMES = [
    'url_len', 'at', 'qmark', 'dash', 'eq', 'dot', 'hash', 'pct', 
    'plus', 'dollar', 'bang', 'star', 'comma', 'double_slash', 
    'abnormal_url', 'https', 'digits', 'letters', 
    'Shortining_Service', 'having_ip_address'
]

def get_manual_features(url):
    clean = url.replace('www.', '')
    features = []
    
    features.append(len(clean))
    for s in ['@','?','-','=','.','#','%','+','$','!','*',',','//']:
        features.append(str(clean).count(s))
        
    try:
        host = urlparse(clean).hostname
        if host and clean.startswith(('http://'+host, 'https://'+host)):
            features.append(0)
        else:
            features.append(1)
    except:
        features.append(1)
        
    scheme = urlparse(clean).scheme
    features.append(1 if str(scheme) == 'https' else 0)
    features.append(sum(c.isdigit() for c in clean))
    features.append(sum(c.isalpha() for c in clean))
    
    match = re.search(r'bit\.ly|goo\.gl|tinyurl|t\.co|ow\.ly|adf\.ly|bitly\.com|tinyurl\.com|cutt\.us|j\.mp', clean, flags=re.I)
    features.append(1 if match else 0)
    
    ip = re.search(r'(\d{1,3}\.){3}\d{1,3}', clean)
    features.append(1 if ip else 0)
    
    return features

def get_urlnet_features(url):
    max_len = 200
    seq = [char2idx.get(c, 0) for c in url[:max_len]]
    seq += [0] * (max_len - len(seq)) 
    return torch.tensor([seq], dtype=torch.long)

def get_base_domain(url):
    try:
        p = urlparse(url)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}/"
        return url
    except:
        return url

# ==========================================
# 4. PREDICTION ENDPOINT
# ==========================================
class UrlRequest(BaseModel):
    urls: list[str]

# 1. Defacement restored to map
LABEL_MAP = {0: "Benign", 1: "Defacement", 2: "Phishing", 3: "Malware"}

@app.post("/predict")
async def predict(request: UrlRequest):
    # 2. Defacement restored to summary (Fixes NaN)
    response = {
        "summary": {"Benign": 0, "Defacement": 0, "Phishing": 0, "Malware": 0},
        "details": []
    }
    
    # Whitelist
    custom_safe_list = [
        "phishtank", "cisco", "virustotal", "github","talosintelligence","youtubekids",
        "stackoverflow", "google", "microsoft", "127.0.0.1", "localhost"
    ]

    for url in request.urls:
        final_label = "Benign"
        model_details = {}
        is_safe = False
        reason = ""

        # Check Whitelists
        if any(site in url.lower() for site in custom_safe_list):
            is_safe = True
            reason = "Verified Safe (Manual List)"
        
        if not is_safe and tranco_list:
            try:
                domain = get_tld(url, as_object=True).fld
                rank = tranco_list.rank(domain)
                if rank != -1 and rank < 20000:
                    is_safe = True
                    reason = f"Trusted Site (Rank #{rank})"
            except: pass

        if is_safe:
            response["summary"]["Benign"] += 1
            response["details"].append({
                "url": url, 
                "status": "Benign", 
                "models": {"System": reason}
            })
            continue

        # AI Models
        try:
            scores = {0: 0, 1: 0, 2: 0, 3: 0} # 1 is Defacement

            def cast_vote(name, cls, weight):
                scores[cls] += weight
                model_details[name] = f"{LABEL_MAP[cls]} (w={weight})"

            df = pd.DataFrame([get_manual_features(url)], columns=FEATURE_NAMES)
            urlnet_input = get_urlnet_features(url)

            # Domain Check
            dom_url = get_base_domain(url)
            if dom_url != url and xgb_model:
                try:
                    dom_df = pd.DataFrame([get_manual_features(dom_url)], columns=FEATURE_NAMES)
                    dtest = xgb.DMatrix(dom_df)
                    pred = xgb_model.predict(dtest)[0]
                    cls = int(np.argmax(pred)) if isinstance(pred, np.ndarray) else int(pred)
                    if cls in [2, 3]:
                        scores[cls] += 2
                        model_details["Domain Analysis"] = f"Suspicious ({LABEL_MAP[cls]})"
                except: pass

            # Full Scan
            if lgbm_model:
                pred = lgbm_model.predict(df)[0]
                cls = int(np.argmax(pred)) if isinstance(pred, np.ndarray) else int(pred)
                cast_vote("LightGBM", cls, 1)

            if xgb_model:
                dtest = xgb.DMatrix(df)
                pred = xgb_model.predict(dtest)[0]
                cls = int(np.argmax(pred)) if isinstance(pred, np.ndarray) else int(pred)
                cast_vote("XGBoost", cls, 1)

            if cat_model:
                cls = int(cat_model.predict(df)[0])
                cast_vote("CatBoost", cls, 1)

            if urlnet_model:
                with torch.no_grad():
                    out = urlnet_model(urlnet_input)
                    cls = torch.argmax(out, 1).item()
                    cast_vote("URLNet", cls, 2)

            if bert_model:
                try:
                    inputs = bert_tokenizer(url, truncation=True, padding="max_length", max_length=64, return_tensors="pt")
                    with torch.no_grad():
                        out = bert_model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])
                    cls = torch.argmax(out, dim=1).item()
                    cast_vote("BERT", cls, 2)
                except: pass

            # Decision Logic
            benign_score = scores[0] + scores[1] # Benign + Defacement are "Not Malware"
            malicious_score = scores[2] + scores[3]

            if malicious_score > benign_score:
                if scores[3] >= scores[2]: final_label = "Malware"
                else: final_label = "Phishing"
            else:
                # If Defacement has high score, you can show it, or default to Benign
                if scores[1] > scores[0]:
                    final_label = "Defacement"
                else:
                    final_label = "Benign"

        except Exception as e:
            print(f"Error: {e}")
            final_label = "Benign"

        if final_label in response["summary"]:
            response["summary"][final_label] += 1
        
        response["details"].append({
            "url": url, 
            "status": final_label, 
            "models": model_details
        })

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)