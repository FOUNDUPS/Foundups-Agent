import sharp from 'sharp';

for (const size of [192, 512]) {
  await sharp('public/favicon.svg')
    .resize(size, size)
    .png({ compressionLevel: 9 })
    .toFile(`public/pwa-icon-${size}.png`);
}
