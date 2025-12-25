import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from PIL import Image
import os

# Создаем директорию
OUTPUT_DIR = "datasets/faces"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Загружаем CelebA датасет
print("Загрузка CelebA датасета...")
dataset = torchvision.datasets.CelebA(
    root='./data',
    split='train',  # 'train', 'valid', 'test'
    download=True,
    transform=transforms.ToTensor()
)

# Сохраняем первые 300 изображений
print(f"Сохранение {min(300, len(dataset))} изображений...")
for i in range(min(300, len(dataset))):
    img_tensor, _ = dataset[i]  # _ это метки атрибутов
    img = transforms.ToPILImage()(img_tensor)
    img.save(os.path.join(OUTPUT_DIR, f"face_{i:03d}.jpg"), "JPEG")
    
    if (i + 1) % 10 == 0:
        print(f"Сохранено: {i + 1}")

print(f"Готово! Сохранено в: {os.path.abspath(OUTPUT_DIR)}")