import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import pandas as pd
import os

# Config
MAX_LEN = 128
BATCH_SIZE = 16
EPOCHS = 4
LEARNING_RATE = 2e-5
PRETRAINED_MODEL = 'bert-base-uncased'

# Tokenizer
tokenizer = BertTokenizer.from_pretrained(PRETRAINED_MODEL)

# Dataset
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
            max_length=MAX_LEN,
            return_tensors='pt'
        )
        age = torch.tensor([item['age'] / 100.0], dtype=torch.float)
        sex_str = str(item['sex']).lower()
        sex = torch.tensor([1.0 if sex_str == 'male' else 0.0], dtype=torch.float)
        label = torch.tensor([item['label']], dtype=torch.float)
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'age': age,
            'sex': sex,
            'label': label
        }

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

def train_model(model, train_loader, val_loader, epochs=EPOCHS):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.BCEWithLogitsLoss()

    for epoch in range(epochs):
        model.train()
        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            age = batch['age'].to(device)
            sex = batch['sex'].to(device)
            labels = batch['label'].to(device)

            outputs = model(input_ids, attention_mask, age, sex).squeeze()
            loss = criterion(outputs, labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        print(f"Epoch {epoch+1}/{epochs} complete. Loss: {loss.item():.4f}")
        evaluate_model(model, val_loader)

def evaluate_model(model, loader):
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            age = batch['age'].to(device)
            sex = batch['sex'].to(device)
            labels = batch['label'].to(device)

            logits = model(input_ids, attention_mask, age, sex).squeeze()
            preds = (torch.sigmoid(logits) > 0.5).float()

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    acc = accuracy_score(all_labels, all_preds)
    prec = precision_score(all_labels, all_preds)
    rec = recall_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds)
    roc = roc_auc_score(all_labels, all_preds)
    print(f"Val Accuracy: {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1: {f1:.4f} | ROC AUC: {roc:.4f}")

def save_model(model, path="adhd_model.pt"):
    torch.save(model.state_dict(), path)

def load_model(model, path="adhd_model.pt"):
    model.load_state_dict(torch.load(path))
    model.eval()
    return model