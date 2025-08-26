import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel
from torch.utils.data import Dataset
import pandas as pd
from adhd_nn_diagnosis_model import ADHDClassifier

PRETRAINED_MODEL = "bert-base-uncased"
MODEL_PATH = "adhd_model.pt"
tokenizer = BertTokenizer.from_pretrained(PRETRAINED_MODEL)


def evaluate_answer_traits(question, answer, age, sex):
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = ADHDClassifier()
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        model.to(device).eval()

        inputs = tokenizer(
            answer,
            return_tensors="pt",
            max_length=128,
            truncation=True,
            padding="max_length"
        )

        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)
        age_tensor = torch.tensor([[age / 100.0]], dtype=torch.float).to(device)
        sex_tensor = torch.tensor([[1.0 if sex.lower() == "male" else 0.0]], dtype=torch.float).to(device)

        output = model(input_ids, attention_mask, age_tensor, sex_tensor)
        score = float(output.squeeze().item())
        tag = "ADHD" if score >= 0.5 else "NON_ADHD"

        return {"trait": tag, "completeness": score}
    except Exception as e:
        print(f"[NN ERROR]: {e}")
        return {"trait": "UNKNOWN", "completeness": 0.0}

# Sample validation function
def validate_guidance_pipeline():
    # Simulate minimal dataframe
    df = pd.DataFrame({
        'response': ["I have trouble focusing", "I never had issues"],
        'age': [25, 40],
        'sex': ['male', 'female'],
        'label': [1, 0]
    })

    # Dataset logic
    class ADHDInterviewDataset(Dataset):
        def __init__(self, dataframe):
            self.data = dataframe

        def __len__(self):
            return len(self.data)

        def __getitem__(self, index):
            item = self.data.iloc[index]
            encoding = tokenizer(
                item['response'],
                truncation=True,
                padding='max_length',
                max_length= 128,
                return_tensors='pt'
            )
            age = torch.tensor([item['age'] / 100.0], dtype=torch.float)
            sex = torch.tensor([1.0 if str(item['sex']).lower() == 'male' else 0.0], dtype=torch.float)
            label = torch.tensor([item['label']], dtype=torch.float)
            return {
                'input_ids': encoding['input_ids'].squeeze(0),
                'attention_mask': encoding['attention_mask'].squeeze(0),
                'age': age,
                'sex': sex,
                'label': label
            }

    # Model logic
    class ADHDClassifier(nn.Module):
        def __init__(self):
            super(ADHDClassifier, self).__init__()
            self.bert = BertModel.from_pretrained(PRETRAINED_MODEL)
            self.dropout = nn.Dropout(0.3)
            self.fc = nn.Linear(self.bert.config.hidden_size + 2, 1)

        def forward(self, input_ids, attention_mask, age, sex):
            outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
            pooled_output = outputs.pooler_output
            concat = torch.cat((pooled_output, age, sex), dim=1)
            x = self.dropout(concat)
            return self.fc(x)
        # Place this BELOW ADHDClassifier but ABOVE any test/demo functions

    try:
        dataset = ADHDInterviewDataset(df)
        sample = dataset[0]
        model = ADHDClassifier()
        model.eval()
        with torch.no_grad():
            out = model(
                sample['input_ids'].unsqueeze(0),
                sample['attention_mask'].unsqueeze(0),
                sample['age'].unsqueeze(0),
                sample['sex'].unsqueeze(0)
            )
        return {"success": True, "output_prob": torch.sigmoid(out).item()}
    except Exception as e:
        return {"success": False, "error": str(e)}

validate_guidance_pipeline()
