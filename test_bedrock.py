import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')

try:
    # Essayer d'invoquer un modèle avec un modelId connu
    response = bedrock.invoke_model(
        modelId='amazon.titan-text-gen-3b',  # Remplacez par un modelId connu
        body=json.dumps({"input_text": "Analyse des rapports financiers"}),
        contentType='application/json'
    )
    result = json.loads(response['body'].read())
    print("Résultat de l'invocation :", result.get('results', [{}])[0].get('generated_text', "Pas de réponse"))
except Exception as e:
    print(f"Erreur lors de l'invocation du modèle : {e}")
