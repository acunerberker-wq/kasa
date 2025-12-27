# -*- coding: utf-8 -*-
"""
Buton PNG İyileştirme Aracı
===========================

Bu script şeffaf arkaplanlı buton PNG'lerini analiz eder ve iyileştirir:
- Bulanıklık, artefact, kenar tırtığı, halo tespiti
- 2x ve 4x upscale (Lanczos + edge-aware sharpening)
- Before/after karşılaştırma görseli

Kullanım:
    python tools/enhance_buttons.py

Gerekli paketler:
    pip install pillow opencv-python numpy

Girdi: ./buttons/
Çıktı: ./buttons_enhanced/
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# PIL import
HAS_PIL = False
try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    pass

if not HAS_PIL:
    print("HATA: Pillow kurulu değil. Kurmak için: pip install pillow")
    sys.exit(1)

# OpenCV import (opsiyonel)
HAS_CV2 = False
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    print("UYARI: OpenCV kurulu değil. Temel özelliklerle devam edilecek.")
    print("Gelişmiş analiz için: pip install opencv-python numpy")
    # numpy'yi PIL için de deneyelim
    try:
        import numpy as np
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False
        print("UYARI: NumPy kurulu değil. Bazı analizler atlanacak.")


# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "buttons"
OUTPUT_DIR = PROJECT_ROOT / "buttons_enhanced"


class ButtonAnalyzer:
    """PNG buton analiz ve iyileştirme sınıfı."""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report: Dict[str, dict] = {}
    
    def analyze_image(self, img_path: Path) -> dict:
        """Tek bir PNG'yi analiz et ve sorunları tespit et."""
        issues = {
            "filename": img_path.name,
            "size": None,
            "has_alpha": False,
            "blur_score": 0.0,
            "noise_score": 0.0,
            "edge_quality": "unknown",
            "halo_detected": False,
            "banding_detected": False,
            "jpeg_artifacts": False,
            "issues_found": [],
            "recommendations": []
        }
        
        try:
            img = Image.open(img_path)
            issues["size"] = img.size
            issues["has_alpha"] = img.mode == "RGBA"
            
            if not issues["has_alpha"]:
                issues["issues_found"].append("Alpha kanalı yok - şeffaflık eksik")
                issues["recommendations"].append("RGBA moduna dönüştür")
            
            # OpenCV ile gelişmiş analiz (eğer mevcutsa)
            if HAS_CV2:
                img_array = np.array(img)
                
                if len(img_array.shape) >= 3 and img_array.shape[2] >= 3:
                    # Bulanıklık tespiti (Laplacian variance)
                    gray = cv2.cvtColor(img_array[:, :, :3], cv2.COLOR_RGB2GRAY)
                    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                    issues["blur_score"] = round(laplacian_var, 2)
                    
                    if laplacian_var < 100:
                        issues["issues_found"].append(f"Bulanık görüntü (skor: {laplacian_var:.1f})")
                        issues["recommendations"].append("Unsharp mask uygula")
                    elif laplacian_var < 300:
                        issues["issues_found"].append(f"Hafif bulanık (skor: {laplacian_var:.1f})")
                    
                    # Gürültü tespiti
                    noise = self._estimate_noise(img_array[:, :, :3])
                    issues["noise_score"] = round(noise, 2)
                    if noise > 5:
                        issues["issues_found"].append(f"Gürültü tespit edildi (skor: {noise:.1f})")
                        issues["recommendations"].append("Hafif denoise uygula")
                    
                    # Kenar kalitesi
                    edges = cv2.Canny(gray, 50, 150)
                    edge_density = np.sum(edges > 0) / edges.size
                    if edge_density < 0.01:
                        issues["edge_quality"] = "düşük"
                        issues["issues_found"].append("Kenar detayları zayıf")
                    elif edge_density > 0.15:
                        issues["edge_quality"] = "gürültülü"
                        issues["issues_found"].append("Kenar gürültüsü var")
                    else:
                        issues["edge_quality"] = "iyi"
                    
                    # Halo tespiti (alpha kenarlarında)
                    if issues["has_alpha"]:
                        halo = self._detect_halo(img_array)
                        issues["halo_detected"] = halo
                        if halo:
                            issues["issues_found"].append("Kenar halosu tespit edildi")
                            issues["recommendations"].append("Alpha kenarlarını temizle")
                    
                    # Banding tespiti
                    banding = self._detect_banding(img_array[:, :, :3])
                    issues["banding_detected"] = banding
                    if banding:
                        issues["issues_found"].append("Gradient banding tespit edildi")
                        issues["recommendations"].append("Dithering ekle")
            else:
                # OpenCV yoksa basit analiz
                issues["issues_found"].append("Gelişmiş analiz için OpenCV gerekli")
                issues["recommendations"].append("pip install opencv-python numpy")
            
            if not issues["issues_found"]:
                issues["issues_found"].append("Görüntü kaliteli görünüyor")
            
        except Exception as e:
            issues["issues_found"].append(f"Analiz hatası: {str(e)}")
        
        return issues
    
    def _estimate_noise(self, img: np.ndarray) -> float:
        """Görüntü gürültüsünü tahmin et (sigma)."""
        if not HAS_CV2:
            return 0.0
        
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        H, W = gray.shape
        
        # Laplacian filtresi ile gürültü tahmini
        M = np.array([[1, -2, 1],
                      [-2, 4, -2],
                      [1, -2, 1]])
        
        sigma = np.sum(np.abs(cv2.filter2D(gray.astype(np.float64), -1, M)))
        sigma = sigma * np.sqrt(0.5 * np.pi) / (6 * (W - 2) * (H - 2))
        
        return sigma
    
    def _detect_halo(self, img: np.ndarray) -> bool:
        """Alpha kenarlarında halo var mı kontrol et."""
        if img.shape[2] < 4:
            return False
        
        alpha = img[:, :, 3]
        rgb = img[:, :, :3]
        
        # Alpha kenarlarını bul
        alpha_edges = cv2.Canny(alpha, 50, 150)
        
        # Kenar piksellerinde parlaklık farkı kontrol et
        edge_coords = np.where(alpha_edges > 0)
        if len(edge_coords[0]) < 10:
            return False
        
        # Kenar bölgesinde beyaz/siyah halo kontrolü
        for i in range(min(100, len(edge_coords[0]))):
            y, x = edge_coords[0][i], edge_coords[1][i]
            if 2 <= y < img.shape[0] - 2 and 2 <= x < img.shape[1] - 2:
                # Çevre piksellerinin parlaklık varyansı
                region = rgb[y-1:y+2, x-1:x+2]
                if np.std(region) > 60:  # Yüksek varyans = potansiyel halo
                    return True
        
        return False
    
    def _detect_banding(self, img: np.ndarray) -> bool:
        """Gradient banding tespit et."""
        if not HAS_CV2:
            return False
        
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Yatay ve dikey gradientler
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Gradient histogram analizi - keskin pikler banding gösterir
        hist_x, _ = np.histogram(np.abs(grad_x).flatten(), bins=50)
        hist_y, _ = np.histogram(np.abs(grad_y).flatten(), bins=50)
        
        # İlk birkaç bin'de yoğunlaşma varsa banding var demektir
        if hist_x[0] > np.sum(hist_x) * 0.9 or hist_y[0] > np.sum(hist_y) * 0.9:
            return True
        
        return False
    
    def enhance_image(self, img_path: Path, scale: int = 2) -> Optional[Image.Image]:
        """Görüntüyü iyileştir ve upscale et."""
        try:
            img = Image.open(img_path).convert("RGBA")
            orig_size = img.size
            new_size = (orig_size[0] * scale, orig_size[1] * scale)
            
            # 1. Upscale (Lanczos - en kaliteli)
            img_upscaled = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 2. RGB ve Alpha kanallarını ayır
            r, g, b, a = img_upscaled.split()
            rgb = Image.merge("RGB", (r, g, b))
            
            # 3. Edge-aware sharpening (Unsharp Mask)
            # Hafif bir unsharp mask - aşırı keskinleştirme yapmadan
            rgb_sharp = rgb.filter(ImageFilter.UnsharpMask(
                radius=1.5,      # Küçük radius = ince detaylar
                percent=80,      # Düşük yüzde = doğal görünüm
                threshold=2      # Düşük threshold = daha çok detay
            ))
            
            # 4. Alpha kanalını da hafifçe keskinleştir (temiz kenarlar için)
            a_sharp = a.filter(ImageFilter.UnsharpMask(
                radius=0.8,
                percent=50,
                threshold=1
            ))
            
            # 5. Birleştir
            r, g, b = rgb_sharp.split()
            result = Image.merge("RGBA", (r, g, b, a_sharp))
            
            # 6. Halo temizliği (alpha kenarlarında)
            result = self._clean_alpha_edges(result)
            
            return result
            
        except Exception as e:
            print(f"  HATA: {img_path.name} işlenemedi: {e}")
            return None
    
    def _clean_alpha_edges(self, img: Image.Image) -> Image.Image:
        """Alpha kenarlarındaki haloları temizle."""
        if img.mode != "RGBA":
            return img
        
        # OpenCV ve NumPy varsa gelişmiş temizlik
        if HAS_CV2:
            img_array = np.array(img)
            alpha = img_array[:, :, 3]
            
            # Yarı saydam pikselleri bul (0 < alpha < 255)
            semi_transparent = (alpha > 0) & (alpha < 255)
            
            if not np.any(semi_transparent):
                return img
            
            result = img_array.copy()
            
            # Alpha kanalına hafif blur + threshold
            alpha_clean = cv2.GaussianBlur(alpha.astype(np.float32), (3, 3), 0.5)
            alpha_clean = np.clip(alpha_clean, 0, 255).astype(np.uint8)
            result[:, :, 3] = alpha_clean
            
            return Image.fromarray(result)
        else:
            # PIL ile basit temizlik
            # Alpha kanalını al ve hafif smooth uygula
            r, g, b, a = img.split()
            # Hafif median filter kenar haloları azaltır
            a_clean = a.filter(ImageFilter.MedianFilter(size=3))
            return Image.merge("RGBA", (r, g, b, a_clean))
    
    def create_comparison(self, original: Image.Image, enhanced: Image.Image, 
                          filename: str) -> Image.Image:
        """Before/After karşılaştırma görseli oluştur."""
        # Her iki görüntüyü aynı boyuta getir
        w1, h1 = original.size
        w2, h2 = enhanced.size
        
        # Comparison için orijinali enhanced boyutuna upscale et
        if w1 != w2:
            original = original.resize((w2, h2), Image.Resampling.NEAREST)
        
        # Yan yana birleştir
        gap = 20
        label_height = 30
        total_width = w2 * 2 + gap
        total_height = h2 + label_height + 10
        
        # Checker pattern arka plan (şeffaflığı göstermek için)
        comparison = Image.new("RGBA", (total_width, total_height), (40, 40, 45, 255))
        
        # Checker pattern
        checker_size = 8
        for y in range(0, total_height, checker_size):
            for x in range(0, total_width, checker_size):
                if (x // checker_size + y // checker_size) % 2 == 0:
                    for py in range(y, min(y + checker_size, total_height)):
                        for px in range(x, min(x + checker_size, total_width)):
                            comparison.putpixel((px, py), (50, 50, 55, 255))
        
        # Görselleri yapıştır
        comparison.paste(original, (0, label_height + 5), original)
        comparison.paste(enhanced, (w2 + gap, label_height + 5), enhanced)
        
        # Etiketler
        draw = ImageDraw.Draw(comparison)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 5), "BEFORE (Original)", fill=(200, 200, 200, 255), font=font)
        draw.text((w2 + gap + 10, 5), "AFTER (Enhanced)", fill=(100, 255, 100, 255), font=font)
        
        # Dosya adı
        draw.text((total_width // 2 - 50, total_height - 20), 
                  filename, fill=(150, 150, 150, 255), font=font)
        
        return comparison
    
    def process_all(self):
        """Tüm PNG'leri işle."""
        png_files = list(self.input_dir.glob("*.png"))
        
        if not png_files:
            print(f"\n❌ '{self.input_dir}' klasöründe PNG dosyası bulunamadı!")
            print("\nLütfen buton PNG'lerini bu klasöre koyun:")
            print(f"   {self.input_dir.absolute()}")
            return
        
        print(f"\n📁 {len(png_files)} PNG dosyası bulundu.\n")
        print("=" * 60)
        
        # Önce analiz
        print("\n📊 ADIM 1: ANALİZ\n")
        for png_file in png_files:
            print(f"🔍 Analiz: {png_file.name}")
            analysis = self.analyze_image(png_file)
            self.report[png_file.name] = analysis
            
            print(f"   Boyut: {analysis['size']}")
            print(f"   Alpha: {'✓' if analysis['has_alpha'] else '✗'}")
            print(f"   Keskinlik skoru: {analysis['blur_score']}")
            print(f"   Sorunlar:")
            for issue in analysis["issues_found"]:
                print(f"     - {issue}")
            print()
        
        # İyileştirme
        print("=" * 60)
        print("\n🔧 ADIM 2: İYİLEŞTİRME\n")
        
        for png_file in png_files:
            print(f"⚙️  İşleniyor: {png_file.name}")
            original = Image.open(png_file).convert("RGBA")
            base_name = png_file.stem
            orig_w, orig_h = original.size
            
            # 2x versiyon
            enhanced_2x = self.enhance_image(png_file, scale=2)
            if enhanced_2x:
                out_2x = self.output_dir / f"{base_name}__2x.png"
                enhanced_2x.save(out_2x, "PNG", compress_level=6)
                print(f"   ✓ {out_2x.name} ({enhanced_2x.size[0]}x{enhanced_2x.size[1]})")
            
            # 4x versiyon (sadece küçük/orta boyutlu dosyalar için)
            # Çok büyük dosyalarda 4x atlayalım (orijinal > 500px herhangi bir kenar)
            max_dim = max(orig_w, orig_h)
            if max_dim <= 500:
                enhanced_4x = self.enhance_image(png_file, scale=4)
                if enhanced_4x:
                    out_4x = self.output_dir / f"{base_name}__4x.png"
                    enhanced_4x.save(out_4x, "PNG", compress_level=6)
                    print(f"   ✓ {out_4x.name} ({enhanced_4x.size[0]}x{enhanced_4x.size[1]})")
            else:
                print(f"   ⏭️  4x atlandı (orijinal {orig_w}x{orig_h} çok büyük)")
            
            # Karşılaştırma görseli (2x ile)
            if enhanced_2x:
                comparison = self.create_comparison(original, enhanced_2x, png_file.name)
                comp_path = self.output_dir / f"{base_name}__comparison.png"
                comparison.save(comp_path, "PNG", compress_level=6)
                print(f"   ✓ {comp_path.name} (karşılaştırma)")
            
            print()
        
        # Rapor kaydet
        report_path = self.output_dir / "analysis_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Analiz raporu: {report_path}")
        
        print("\n" + "=" * 60)
        print("✅ İşlem tamamlandı!")
        print(f"📁 Çıktı klasörü: {self.output_dir.absolute()}")


def main():
    if not HAS_PIL:
        print("\n❌ Pillow paketi gerekli. Kurmak için:")
        print("   pip install pillow")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎨 BUTON PNG İYİLEŞTİRME ARACI")
    print("=" * 60)
    
    analyzer = ButtonAnalyzer(INPUT_DIR, OUTPUT_DIR)
    analyzer.process_all()


if __name__ == "__main__":
    main()
