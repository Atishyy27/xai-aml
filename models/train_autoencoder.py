# models/train_autoencoder.py
import torch
import torch.nn as nn
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib

# --- 1. Define the Autoencoder Architecture ---
class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 6),
            nn.ReLU(),
            nn.Linear(6, 3)  # Bottleneck layer
        )
        self.decoder = nn.Sequential(
            nn.Linear(3, 6),
            nn.ReLU(),
            nn.Linear(6, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

# --- 2. Training Script ---
if __name__ == "__main__":
    # load features
    df = pd.read_csv("account_features.csv").set_index("account_id")

    # Preprocessing: fit & save scaler
    scaler = StandardScaler()
    X = scaler.fit_transform(df.values)
    joblib.dump(scaler, "scaler.pkl")   # <<-- important: save the scaler

    X_tensor = torch.FloatTensor(X)

    # Model Initialization
    input_dim = X.shape[1]
    model = Autoencoder(input_dim)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # Training Loop
    print("Training Autoencoder...")
    num_epochs = 50
    for epoch in range(num_epochs):
        outputs = model(X_tensor)
        loss = criterion(outputs, X_tensor)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{epoch + 1}/{num_epochs}], Loss: {loss.item():.4f}')

    # Save the trained model
    torch.save(model.state_dict(), "autoencoder.pth")
    print("Autoencoder model trained and saved to autoencoder.pth")
    print("Scaler saved to scaler.pkl")
