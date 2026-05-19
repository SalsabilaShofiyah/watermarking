# Digital Watermarking II2240 Sistem Multimedia

**Nama:** Salsabila Shofiyah  
**NIM:** 18224088  
**Kelas:** K-02  
**Mata Kuliah:** II2240 Sistem Multimedia

---

## Deskripsi Project

Project ini mengimplementasikan dua teknik digital watermarking pada gambar dan membandingkan kualitasnya terhadap kompresi JPEG pada berbagai Quality Factor (QF).


## Metode yang Diimplementasikan

### 1. LSB (Least Significant Bit)

Bekerja dengan memodifikasi bit terkecil (bit ke-0) dari channel merah setiap pixel pada area 32x32 pixel pada pojok di kiri atas. Perubahan pixel maksimal ±1 sehingga tidak terlihat secara visual. Tidak tahan dengan kompresi JPEG.

### 2. DCT Mid-Band

Bekerja dengan menyisipkan koefisien frekuensi menengah (mid-band) pada blok DCT 8x8. Lebih tahan terhadap kompresi JPEG karena JPEG sendiri menggunakan DCT.

---

## Tools yang Digunakan

| Tools | Kegunaan |
|---------|----------|
| NumPy | Operasi array dan perhitungan matematis |
| Pillow | Membaca dan menyimpan gambar, codec JPEG |
| Matplotlib | Visualisasi grafik evaluasi |

---

## Cara Menjalankan

**1. Install tools yang dibutuhkan**

```
pip install numpy pillow matplotlib
```

**2. Menyiapkan file pyhton dan foto yang ingin diberi watermark dalam satu folder**

```
watermarking.py
Foto resmi.JPEG
```

**3. Jalankan source code di terminal**

```
python3 watermarking.py
```

Proses memakan waktu sekitar 1-2 menit karena DCT memproses 1024 blok 8x8 secara manual. Semua hasil tersimpan otomatis di subfolder `result/`.

---

## Output di Folder result/

| File | Deskripsi |
|------|-----------|
| original_face.png | Foto asli setelah di-resize ke 256x256 pixel |
| watermark_32x32.png | Pola watermark biner 32x32 pixel (putih = 1, hitam = 0) |
| foto_watermarked_lsb.png | Foto dengan watermark LSB |
| foto_watermarked_dct.png | Foto dengan watermark DCT mid-band |
| watermarking_evaluation.png | Grafik BER, NC, dan PSNR per QF |

---

## Metrik Evaluasi

**BER (Bit Error Rate)** adalah proporsi bit yang salah saat ekstraksi. Nilai 0.0 berarti ekstraksi sempurna, sedangkan nilai 0.5 berarti sama seperti ekstraksi yang acak.

```
BER = jumlah bit salah / total bit watermark
```

**NC (Normalized Correlation)** adalah kemiripan watermark asli dibandingkan dengan hasil ekstraksi. Nilai 1.0 berarti identik sempurna.

```
NC = sum(W x W') / sqrt(sum(W^2) x sum(W'^2))
```

**PSNR** adalah kualitas visual gambar setelah kompresi. Semakin tinggi nilainya, semakin mirip dengan gambar asli sebelum di watermark.

```
PSNR = 10 x log10(255^2 / MSE)
```

---

## Hasil Evaluasi

| QF | BER LSB | Status LSB | BER DCT | Status DCT | PSNR (dB) |
|----|---------|------------|---------|------------|-----------|
| 5 | 0.519 | GAGAL | 0.509 | GAGAL | 26.59 |
| 10 | 0.519 | GAGAL | 0.501 | GAGAL | 29.28 |
| 20 | 0.519 | GAGAL | 0.266 | DEGRADASI | 31.82 |
| 30 | 0.519 | GAGAL | 0.140 | DEGRADASI | 34.98 |
| 40 | 0.519 | GAGAL | 0.066 | BERHASIL | 36.21 |
| 50 | 0.481 | GAGAL | 0.030 | BERHASIL | 36.41 |
| 60 | 0.519 | GAGAL | 0.000 | BERHASIL | 37.87 |
| 70-100 | ~0.48 | GAGAL | 0.000 | BERHASIL | 38-56 |

QF kritis: watermark DCT tidak dapat diekstrak pada QF lebih kecil atau sama dengan 10.

---

## Kesimpulan

Dari dua teknik yang dilakukan untuk watermarking, LSB lebih simple dan cepat namun tidak tahan terhadap kompresi JPEG sama sekali, karena proses DCT dan quantization pada JPEG langsung merusak nilai pixel. DCT jauh lebih baik hasilnya karena menyisipkan watermark di frekuensi, kemungkinan teknik ini gagal saat QF bernilai 10 atau lebih rendah.
