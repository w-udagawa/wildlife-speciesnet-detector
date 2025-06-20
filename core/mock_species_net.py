"""
SpeciesNet代替モック - テスト用
Wildlife Detector GUI改善版のテスト用に一時的なSpeciesNetモック
"""

class MockSpeciesNet:
    """SpeciesNet のモッククラス（テスト用）"""
    
    def __init__(self):
        self.model_loaded = True
        
    def predict(self, image_path, confidence_threshold=0.5):
        """予測結果のモック"""
        import random
        import os
        
        # テスト用のモック検出結果
        mock_results = [
            {
                'species': 'Ardea alba',
                'common_name': 'Great Egret',
                'scientific_name': 'Ardea alba',
                'confidence': random.uniform(0.6, 0.95),
                'category': 'Bird'
            },
            {
                'species': 'Corvus corvax',
                'common_name': 'Common Raven', 
                'scientific_name': 'Corvus corvax',
                'confidence': random.uniform(0.5, 0.8),
                'category': 'Bird'
            }
        ]
        
        # ランダムに検出ありなしを決定
        if random.random() > 0.3:  # 70%の確率で検出
            return [random.choice(mock_results)]
        else:
            return []
    
    def load_model(self):
        """モデル読み込みのモック"""
        return True

# speciesnet パッケージのモック
class MockSpeciesNetModule:
    def __init__(self):
        self.SpeciesNet = MockSpeciesNet

# モックモジュールをsys.modulesに登録
import sys
sys.modules['speciesnet'] = MockSpeciesNetModule()

print("🔧 SpeciesNet モック モジュールが読み込まれました")
print("📝 これはテスト用の代替モジュールです")
