import torch
import torch.nn as nn
import pandas as pd
from torch.utils.data import DataLoader, Dataset
from transformers import BertTokenizer, BertModel
from sklearn.model_selection import train_test_split
from adhd_nn_diagnosis_model import ADHDClassifier

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

class InterviewDataset(Dataset):
    def __init__(self, df):
        self.data = df

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        encoding = tokenizer(
            row["response"],
            truncation=True,
            padding="max_length",
            max_length=128,
            return_tensors="pt"
        )
        age = torch.tensor([row["age"] / 100.0])
        sex = torch.tensor([1.0 if row["sex"] == "male" else 0.0])
        label = torch.tensor([row["label"]], dtype=torch.float)
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "age": age,
            "sex": sex,
            "label": label
        }

    def __len__(self):
        return len(self.data)

def train():
    df = pd.read_csv("your_training_data.csv")  # ensure this exists
    train_df, val_df = train_test_split(df, test_size=0.2)

    train_loader = DataLoader(InterviewDataset(train_df), batch_size=16)
    val_loader = DataLoader(InterviewDataset(val_df), batch_size=16)

    model = ADHDClassifier()
    model.to("cuda" if torch.cuda.is_available() else "cpu")

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    loss_fn = nn.BCEWithLogitsLoss()

    for epoch in range(3):
        model.train()
        for batch in train_loader:
            ids = batch["input_ids"]
            mask = batch["attention_mask"]
            age = batch["age"]
            sex = batch["sex"]
            labels = batch["label"]

            ids, mask, age, sex, labels = [x.to("cuda" if torch.cuda.is_available() else "cpu") for x in (ids, mask, age, sex, labels)]

            optimizer.zero_grad()
            outputs = model(ids, mask, age, sex).squeeze()
            loss = loss_fn(outputs, labels)
            loss.backward()
            optimizer.step()

        print(f"Epoch {epoch+1} | Loss: {loss.item():.4f}")

    torch.save(model.state_dict(), "adhd_model.pt")
    print("✅ Model saved to adhd_model.pt")

if __name__ == "__main__":
    train()
