"""당신이 만들 간단한 AI 모델의 자리.

지금은 데모용 더미 로직입니다. 실제로는 이 함수 안에서
- 저장된 모델 파일 로드 (joblib.load / torch.load / tf.keras.load_model 등)
- 전처리 → 예측 → 후처리
를 수행하고 결과를 dict로 반환하면 됩니다.
Tool Calling은 이 함수의 반환값을 그대로 LLM에게 전달합니다.
"""
from typing import Dict, Any


# 예: 모듈 로드 시 한 번만 모델을 메모리에 올림
# import joblib
# _model = joblib.load("model.pkl")


def predict(input_value: float) -> Dict[str, Any]:
    """입력값 하나를 받아 예측 결과를 반환하는 데모 모델.

    실제 구현 예시:
        pred = _model.predict([[input_value]])[0]
        return {"prediction": float(pred)}
    """
    # --- 데모 로직: 입력값의 제곱 + 상수 ---
    result = input_value ** 2 + 3.14
    return {
        "input": input_value,
        "prediction": round(result, 4),
        "model": "demo_quadratic_v1",
    }
