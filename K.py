from PIL import Image, ImageFilter, ImageEnhance, ImageOps

img = Image.open("map.JPG")

# Step 1: edge enhancement
img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)

# Step 2: posterize (reduce colors)
img = ImageOps.posterize(img, 6)  # 4–6 levels looks good

# Step 3: boost contrast and color
img = ImageEnhance.Contrast(img).enhance(3.5)
img = ImageEnhance.Color(img).enhance(0.7)

# Step 4: optional blur smooth edges
img = img.filter(ImageFilter.SMOOTH_MORE)

# Save and load into pygame
img.save("map_cartooned.png")