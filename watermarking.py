"""
Digital Image Watermarking - Tugas Multimedia Systems
======================================================
DUA METODE:
  1. LSB (Least Significant Bit) - domain spasial
  2. DCT Mid-Band - domain frekuensi (lebih tahan JPEG)

Evaluasi JPEG compression di berbagai Quality Factor (QF).
Semua implementasi dari scratch tanpa library watermarking.
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import io
import os


# ============================================================
# BUAT FOLDER RESULT OTOMATIS
# ============================================================

os.makedirs('result', exist_ok=True)


# ============================================================
# 1. LOAD FOTO ASLI
# ============================================================

def load_photo(path='Foto resmi.JPEG', size=256):
    """
    Load foto dari file dan resize ke ukuran size x size.
    Ukuran harus kelipatan 8 agar DCT 8x8 bisa berjalan sempurna.
    """
    img = Image.open(path).convert('RGB')
    img = img.resize((size, size), Image.LANCZOS)
    return np.array(img)


# ============================================================
# 2. GENERATE WATERMARK BINER ACAK
# ============================================================

def generate_binary_watermark(size, seed=42):
    """
    Generate pola watermark biner acak berukuran size x size.
    Seed tetap agar watermark bisa direproduksi saat ekstraksi.
    """
    np.random.seed(seed)
    return np.random.randint(0, 2, (size, size), dtype=np.uint8)


# ============================================================
# 3. METODE A - LSB SPATIAL DOMAIN
# ============================================================

def embed_lsb(image_array, watermark):
    """
    Sisipkan watermark ke LSB (bit ke-0) channel merah (R).
    Setiap piksel hanya berubah nilai maksimal +1 atau -1
    sehingga secara visual tidak terlihat perbedaannya.
    """
    wm_h, wm_w = watermark.shape
    result = image_array.copy()
    red = result[:wm_h, :wm_w, 0].copy()
    red = (red & 0b11111110) | (watermark & 1)
    result[:wm_h, :wm_w, 0] = red
    return result


def extract_lsb(image_array, wm_h, wm_w):
    """Ambil LSB dari channel merah sebagai watermark yang diekstrak."""
    return (image_array[:wm_h, :wm_w, 0] & 1).astype(np.uint8)


# ============================================================
# 4. METODE B - DCT MID-BAND (implementasi manual dari rumus)
# ============================================================

def _make_dct_matrix():
    """
    Bangun matriks DCT-II 8x8 dari rumus standar JPEG.
    Rumus: D[u,x] = C(u) * cos(pi*(2x+1)*u / 16)
    di mana C(0) = 1/sqrt(2), C(u>0) = 1
    """
    N = 8
    D = np.zeros((N, N))
    for u in range(N):
        cu = (1 / np.sqrt(2)) if u == 0 else 1.0
        for x in range(N):
            D[u, x] = cu * np.cos(np.pi * (2 * x + 1) * u / 16)
    D *= 0.5
    return D


_D  = _make_dct_matrix()
_DT = _D.T


def dct2_8x8(block):
    """DCT-II 2D pada blok 8x8 menggunakan perkalian matriks."""
    return _D @ block.astype(np.float64) @ _DT


def idct2_8x8(dct_block):
    """Inverse DCT-II 2D pada blok 8x8."""
    return _DT @ dct_block @ _D


# Posisi mid-band dalam blok DCT 8x8 (frekuensi menengah)
MID_BAND = [(1,2),(2,1),(3,0),(2,3),(1,4),(0,3),(0,5),(1,3)]


def embed_dct(image_array, watermark, alpha=20.0):
    """
    Sisipkan watermark ke koefisien mid-band DCT blok 8x8 pada channel Y.

    Langkah:
    1. Konversi RGB ke YCbCr, ambil channel Y (luminans)
    2. Potong Y jadi blok 8x8, DCT tiap blok
    3. Ubah bit watermark ke bipolar: 0 menjadi -1, 1 menjadi +1
    4. Tambahkan (alpha x bit) ke koefisien mid-band
    5. IDCT tiap blok, rekonstruksi gambar ke RGB
    """
    img_ycbcr = np.array(Image.fromarray(image_array).convert('YCbCr'))
    y  = img_ycbcr[:, :, 0].astype(np.float64)
    cb = img_ycbcr[:, :, 1]
    cr = img_ycbcr[:, :, 2]

    h, w    = y.shape
    wm_h, wm_w = watermark.shape
    wm_bipolar = (watermark.astype(np.float64) * 2) - 1

    bit_idx    = 0
    total_bits = wm_h * wm_w
    y_mod      = y.copy()

    for by in range(0, h - 7, 8):
        for bx in range(0, w - 7, 8):
            if bit_idx >= total_bits:
                break
            blk     = y_mod[by:by+8, bx:bx+8]
            dct_blk = dct2_8x8(blk)
            for (u, v) in MID_BAND:
                if bit_idx >= total_bits:
                    break
                wy = bit_idx // wm_w
                wx = bit_idx %  wm_w
                dct_blk[u, v] += alpha * wm_bipolar[wy, wx]
                bit_idx += 1
            y_mod[by:by+8, bx:bx+8] = idct2_8x8(dct_blk)
        if bit_idx >= total_bits:
            break

    y_mod = np.clip(y_mod, 0, 255)
    ycbcr_out = np.stack(
        [y_mod, cb.astype(np.float64), cr.astype(np.float64)], axis=2
    ).astype(np.uint8)
    return np.array(Image.fromarray(ycbcr_out, 'YCbCr').convert('RGB'))


def extract_dct(original_array, watermarked_array, wm_h, wm_w, alpha=20.0):
    """
    Ekstrak watermark dari selisih koefisien DCT gambar asli vs watermarked.
    Jika selisih positif maka bit = 1, jika negatif maka bit = 0.
    """
    def get_y(arr):
        return np.array(
            Image.fromarray(arr).convert('YCbCr')
        ).astype(np.float64)[:, :, 0]

    y_o = get_y(original_array)
    y_w = get_y(watermarked_array)
    h, w = y_o.shape

    extracted  = np.zeros((wm_h, wm_w), dtype=np.uint8)
    bit_idx    = 0
    total_bits = wm_h * wm_w

    for by in range(0, h - 7, 8):
        for bx in range(0, w - 7, 8):
            if bit_idx >= total_bits:
                break
            d_o = dct2_8x8(y_o[by:by+8, bx:bx+8])
            d_w = dct2_8x8(y_w[by:by+8, bx:bx+8])
            for (u, v) in MID_BAND:
                if bit_idx >= total_bits:
                    break
                wy = bit_idx // wm_w
                wx = bit_idx %  wm_w
                extracted[wy, wx] = 1 if (d_w[u, v] - d_o[u, v]) > 0 else 0
                bit_idx += 1
        if bit_idx >= total_bits:
            break

    return extracted


# ============================================================
# 5. JPEG COMPRESSION
# ============================================================

def compress_jpeg(image_array, quality):
    """
    Kompres gambar dengan JPEG pada quality factor tertentu.
    Menggunakan buffer memori (BytesIO) sehingga tidak menyentuh disk.
    """
    img_pil = Image.fromarray(image_array.astype(np.uint8))
    buf     = io.BytesIO()
    img_pil.save(buf, format='JPEG', quality=quality, subsampling=0)
    file_size_kb = buf.tell() / 1024
    buf.seek(0)
    return np.array(Image.open(buf)), file_size_kb


# ============================================================
# 6. METRIK EVALUASI
# ============================================================

def compute_ber(orig_wm, ext_wm):
    """
    Bit Error Rate: proporsi bit yang berbeda.
    0.0 = sempurna, 0.5 = setara noise acak.
    """
    return np.sum(orig_wm != ext_wm) / orig_wm.size


def compute_nc(orig_wm, ext_wm):
    """
    Normalized Correlation: korelasi antara watermark asli dan ekstraksi.
    1.0 = identik, 0.0 = tidak berkorelasi.
    """
    o   = orig_wm.astype(np.float64)
    e   = ext_wm.astype(np.float64)
    num = np.sum(o * e)
    den = np.sqrt(np.sum(o**2) * np.sum(e**2))
    return num / den if den != 0 else 0.0


def compute_psnr(orig, comp):
    """
    Peak Signal-to-Noise Ratio dalam dB.
    Makin tinggi = gambar terkompresi makin mirip aslinya.
    """
    mse = np.mean((orig.astype(np.float64) - comp.astype(np.float64))**2)
    return float('inf') if mse == 0 else 10 * np.log10(255**2 / mse)


# ============================================================
# 7. VISUALISASI
# ============================================================

def make_visualization(orig, wm_lsb, wm_dct, watermark,
                       qf_vals, ber_lsb, ber_dct,
                       nc_lsb, nc_dct, psnr_vals,
                       ext_lsb_list, ext_dct_list, comp_list,
                       filesize_list):

    BG    = '#0f0f1a'
    PANEL = '#1a1a2e'
    TC    = '#e0e0ff'
    LC    = '#a0a0c0'
    GOOD  = '#4fc3f7'
    MED   = '#ffb74d'
    BAD   = '#ef5350'
    DCT_C = '#ce93d8'
    LSB_C = '#80cbc4'

    fig = plt.figure(figsize=(24, 26))
    fig.patch.set_facecolor(BG)
    gs  = gridspec.GridSpec(5, 5, figure=fig,
                            hspace=0.50, wspace=0.35,
                            top=0.94, bottom=0.04,
                            left=0.04, right=0.97)

    def style_ax(ax):
        ax.set_facecolor(PANEL)
        for sp in ax.spines.values():
            sp.set_edgecolor('#333366')
        ax.tick_params(colors=LC, labelsize=8)

    WM_SIZE = watermark.shape[0]

    # Baris 0: foto asli, watermark, embed LSB, embed DCT, diff
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(orig)
    ax.set_title('Foto Wajah Asli\n(256x256)', color=TC, fontsize=9, fontweight='bold')
    ax.axis('off')

    ax = fig.add_subplot(gs[0, 1])
    ax.imshow(watermark, cmap='gray', vmin=0, vmax=1)
    ax.set_title(f'Watermark Biner\n({WM_SIZE}x{WM_SIZE} = {WM_SIZE*WM_SIZE} bit)', color=TC, fontsize=9, fontweight='bold')
    ax.axis('off')

    ax = fig.add_subplot(gs[0, 2])
    ax.imshow(wm_lsb)
    ax.set_title('Setelah LSB Embed\n(Channel R, bit ke-0)', color=TC, fontsize=9, fontweight='bold')
    ax.axis('off')

    ax = fig.add_subplot(gs[0, 3])
    ax.imshow(wm_dct)
    ax.set_title('Setelah DCT Embed\n(Mid-band, alpha=20)', color=TC, fontsize=9, fontweight='bold')
    ax.axis('off')

    diff = np.clip(
        np.abs(orig.astype(np.int16) - wm_dct.astype(np.int16)) * 20, 0, 255
    ).astype(np.uint8)
    ax = fig.add_subplot(gs[0, 4])
    ax.imshow(diff)
    ax.set_title('Perbedaan DCT x20\n(perubahan sangat halus)', color=TC, fontsize=9, fontweight='bold')
    ax.axis('off')

    # Baris 1: foto terkompresi di 5 QF
    show_idx = [0, 3, 6, 9, 13]
    for col, idx in enumerate(show_idx):
        qf = qf_vals[idx]
        ax = fig.add_subplot(gs[1, col])
        ax.imshow(comp_list[idx])
        ax.set_title(
            f'QF={qf} | PSNR={psnr_vals[idx]:.1f}dB\nSize={filesize_list[idx]:.0f}KB',
            color=TC, fontsize=8.5
        )
        ax.axis('off')

    # Baris 2: watermark DCT terekstrak per QF
    for col, idx in enumerate(show_idx):
        qf = qf_vals[idx]
        ax = fig.add_subplot(gs[2, col])
        ax.imshow(ext_dct_list[idx], cmap='gray', vmin=0, vmax=1)
        bd = ber_dct[idx]
        nd = nc_dct[idx]
        st = "BERHASIL" if bd < 0.1 else ("DEGRADASI" if bd < 0.3 else "GAGAL")
        c  = GOOD if bd < 0.1 else (MED if bd < 0.3 else BAD)
        ax.set_title(
            f'Ekstrak DCT @ QF={qf}\n{st} | BER={bd:.3f} | NC={nd:.3f}',
            color=c, fontsize=8.5
        )
        ax.axis('off')

    # Baris 3: BER plot
    ax_ber = fig.add_subplot(gs[3, :2])
    style_ax(ax_ber)
    ax_ber.plot(qf_vals, ber_lsb, color=LSB_C, lw=2.5, marker='o', ms=5, label='LSB Spasial')
    ax_ber.plot(qf_vals, ber_dct, color=DCT_C, lw=2.5, marker='s', ms=5, label='DCT Mid-Band')
    ax_ber.axhline(0.1, color=GOOD, ls='--', lw=1.2, alpha=0.8, label='Threshold BERHASIL (BER<0.1)')
    ax_ber.axhline(0.3, color=BAD,  ls='--', lw=1.2, alpha=0.8, label='Threshold GAGAL (BER>0.3)')
    ax_ber.axhline(0.5, color='white', ls=':', lw=1, alpha=0.4, label='Level random noise (0.5)')
    ax_ber.set_xlabel('Quality Factor (QF)', color=LC)
    ax_ber.set_ylabel('Bit Error Rate (BER)', color=LC)
    ax_ber.set_title('BER vs Quality Factor\nLSB vs DCT Mid-Band', color=TC, fontsize=10, fontweight='bold')
    ax_ber.legend(fontsize=7.5, facecolor=PANEL, labelcolor=LC)
    ax_ber.set_xlim(2, 102)

    # NC plot
    ax_nc = fig.add_subplot(gs[3, 2:4])
    style_ax(ax_nc)
    ax_nc.plot(qf_vals, nc_lsb, color=LSB_C, lw=2.5, marker='o', ms=5, label='LSB')
    ax_nc.plot(qf_vals, nc_dct, color=DCT_C, lw=2.5, marker='s', ms=5, label='DCT')
    ax_nc.axhline(0.75, color=GOOD, ls='--', lw=1.2, alpha=0.8, label='NC>=0.75: valid')
    ax_nc.set_xlabel('Quality Factor (QF)', color=LC)
    ax_nc.set_ylabel('Normalized Correlation (NC)', color=LC)
    ax_nc.set_title('Normalized Correlation vs QF', color=TC, fontsize=10, fontweight='bold')
    ax_nc.legend(fontsize=7.5, facecolor=PANEL, labelcolor=LC)
    ax_nc.set_ylim(0, 1.05)
    ax_nc.set_xlim(2, 102)

    # PSNR plot
    ax_psnr = fig.add_subplot(gs[3, 4])
    style_ax(ax_psnr)
    ax_psnr.plot(qf_vals, psnr_vals, color='#a5d6a7', lw=2.5, marker='D', ms=4)
    ax_psnr.set_xlabel('QF', color=LC)
    ax_psnr.set_ylabel('PSNR (dB)', color=LC)
    ax_psnr.set_title('Kualitas Gambar\nvs QF', color=TC, fontsize=10, fontweight='bold')

    # Baris 4: perbandingan watermark asli vs ekstrak
    mid_idx = len(qf_vals) // 2
    cases = [
        (watermark,          f'Watermark Asli\n({WM_SIZE}x{WM_SIZE} bit)',         TC),
        (ext_lsb_list[-1],   f'LSB @ QF=100\nBER={ber_lsb[-1]:.3f} (SELALU GAGAL)', BAD),
        (ext_dct_list[-1],   f'DCT @ QF=100\nBER={ber_dct[-1]:.3f} NC={nc_dct[-1]:.3f}',
         GOOD if ber_dct[-1] < 0.1 else MED),
        (ext_dct_list[mid_idx], f'DCT @ QF={qf_vals[mid_idx]}\nBER={ber_dct[mid_idx]:.3f} NC={nc_dct[mid_idx]:.3f}',
         GOOD if ber_dct[mid_idx] < 0.1 else (MED if ber_dct[mid_idx] < 0.3 else BAD)),
        (ext_dct_list[0],    f'DCT @ QF=5\nBER={ber_dct[0]:.3f} (QF terlalu rendah)', BAD),
    ]
    for col, (data, title, color) in enumerate(cases):
        ax = fig.add_subplot(gs[4, col])
        ax.imshow(data, cmap='gray', vmin=0, vmax=1)
        ax.set_title(title, color=color, fontsize=8.5, fontweight='bold')
        ax.axis('off')

    fig.text(0.5, 0.965,
             'Watermarking pada Foto Wajah - LSB Spasial vs DCT Mid-Band | Evaluasi JPEG QF',
             ha='center', color='white', fontsize=13, fontweight='bold')

    plt.savefig('result/watermarking_evaluation.png',
                dpi=120, bbox_inches='tight', facecolor=BG)
    plt.close()
    print("Visualisasi disimpan ke result/watermarking_evaluation.png")


# ============================================================
# 8. MAIN - JALANKAN SEMUA
# ============================================================

def main():
    IMG_SIZE = 256   # Ukuran resize foto (harus kelipatan 8)
    WM_SIZE  = 32    # Ukuran watermark 32x32 = 1024 bit
    ALPHA    = 20.0  # Kekuatan embedding DCT

    print(">>> Load foto asli Foto resmi.JPEG dan resize ke 256x256...")
    original = load_photo('Foto resmi.JPEG', size=IMG_SIZE)

    print(f">>> Generate watermark biner {WM_SIZE}x{WM_SIZE}...")
    watermark = generate_binary_watermark(WM_SIZE, seed=42)

    print(">>> [Metode 1] Embed watermark dengan LSB...")
    wm_lsb = embed_lsb(original, watermark)

    print(">>> [Metode 2] Embed watermark dengan DCT mid-band...")
    print("    (proses 1024 blok 8x8, harap tunggu beberapa detik...)")
    wm_dct = embed_dct(original, watermark, alpha=ALPHA)

    # Verifikasi sebelum kompresi
    e_lsb0 = extract_lsb(wm_lsb, WM_SIZE, WM_SIZE)
    e_dct0 = extract_dct(original, wm_dct, WM_SIZE, WM_SIZE, alpha=ALPHA)
    print(f"    BER LSB tanpa kompresi: {compute_ber(watermark, e_lsb0):.6f} (harus 0.0)")
    print(f"    BER DCT tanpa kompresi: {compute_ber(watermark, e_dct0):.6f} (harus 0.0)")

    qf_values = [5, 10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100]

    ber_lsb_list, ber_dct_list = [], []
    nc_lsb_list,  nc_dct_list  = [], []
    psnr_list, filesize_list   = [], []
    ext_lsb_list, ext_dct_list, comp_list = [], [], []

    print(f"\n>>> Evaluasi kompresi JPEG pada {len(qf_values)} nilai QF...")
    for qf in qf_values:
        c_lsb, sz = compress_jpeg(wm_lsb, qf)
        c_dct, _  = compress_jpeg(wm_dct, qf)
        comp_list.append(c_lsb)
        filesize_list.append(sz)

        el = extract_lsb(c_lsb, WM_SIZE, WM_SIZE)
        ed = extract_dct(original, c_dct, WM_SIZE, WM_SIZE, alpha=ALPHA)
        ext_lsb_list.append(el)
        ext_dct_list.append(ed)

        ber_lsb_list.append(compute_ber(watermark, el))
        ber_dct_list.append(compute_ber(watermark, ed))
        nc_lsb_list.append(compute_nc(watermark, el))
        nc_dct_list.append(compute_nc(watermark, ed))
        psnr_list.append(compute_psnr(original, c_lsb))

        print(f"    QF={qf:3d} | BER_LSB={ber_lsb_list[-1]:.4f} | BER_DCT={ber_dct_list[-1]:.4f} | PSNR={psnr_list[-1]:.2f}dB | Size={sz:.1f}KB")

    # Laporan teks
    print("\n" + "="*74)
    print("  LAPORAN EVALUASI WATERMARKING")
    print("="*74)
    print(f"{'QF':>4} | {'BER_LSB':>8} | {'Status LSB':>10} | {'BER_DCT':>8} | {'Status DCT':>10} | {'PSNR':>7}")
    print("-"*74)
    for i, qf in enumerate(qf_values):
        bl = ber_lsb_list[i]
        bd = ber_dct_list[i]
        sl = "BERHASIL" if bl < 0.1 else ("DEGRADASI" if bl < 0.3 else "GAGAL")
        sd = "BERHASIL" if bd < 0.1 else ("DEGRADASI" if bd < 0.3 else "GAGAL")
        print(f"{qf:>4} | {bl:>8.4f} | {sl:>10} | {bd:>8.4f} | {sd:>10} | {psnr_list[i]:>7.2f}")
    print("="*74)

    fail_dct = [qf_values[i] for i, b in enumerate(ber_dct_list) if b > 0.3]
    ok_dct   = [qf_values[i] for i, b in enumerate(ber_dct_list) if b < 0.1]
    print(f"\nDCT BERHASIL diekstrak (BER<0.1) : QF = {ok_dct}")
    print(f"DCT GAGAL diekstrak   (BER>0.3) : QF = {fail_dct}")
    print("LSB selalu GAGAL karena JPEG merusak LSB via DCT quantization")

    # Simpan foto-foto hasil ke folder result
    Image.fromarray(original).save('result/original_face.png')
    Image.fromarray(wm_lsb).save('result/foto_watermarked_lsb.png')
    Image.fromarray(wm_dct).save('result/foto_watermarked_dct.png')
    Image.fromarray((watermark * 255).astype(np.uint8)).save('result/watermark_32x32.png')
    print("\nFoto disimpan ke folder result/")

    print("\n>>> Membuat visualisasi evaluasi lengkap...")
    make_visualization(
        original, wm_lsb, wm_dct, watermark,
        qf_values, ber_lsb_list, ber_dct_list,
        nc_lsb_list, nc_dct_list, psnr_list,
        ext_lsb_list, ext_dct_list, comp_list,
        filesize_list
    )

    print("\nSemua output tersimpan di folder result/")
    print("  result/watermarking_evaluation.png")
    print("  result/original_face.png")
    print("  result/foto_watermarked_lsb.png")
    print("  result/foto_watermarked_dct.png")
    print("  result/watermark_32x32.png")


if __name__ == "__main__":
    main()