# Roteiro para gravar a sua voz

Grave **cada frase em um arquivo separado**, com este nome (qualquer formato: wav, mp3, m4a, ogg):

| Arquivo | Frase | Duração ideal |
|---|---|---|
| `frase_0` | Quatro fatos do Minecraft que quase ninguém sabe! | ~3 s |
| `frase_1` | A golden dandelion faz filhotes pararem de crescer. Usada de novo, eles voltam a crescer. | ~5 s |
| `frase_2` | O som do Creaking foi feito com pretzel, cadeira rangendo e dedos estalando. | ~4,5 s |
| `frase_3` | O golem de cobre perdeu a votação de mobs e só entrou no jogo anos depois. | ~4,5 s |
| `frase_4` | O ghast seco? A própria Mojang brinca que ainda investiga: restos, ovo ou outra coisa. | ~5 s |
| `frase_5` | Segue pra mais fatos! | ~1,5 s |

Dicas: lugar silencioso, microfone perto (um palmo), energia alta e ritmo animado (é um vídeo curto),
pode deixar 1 s de silêncio antes e depois (eu corto). "Golden dandelion" pode falar em inglês, como no jogo.
Se a soma passar de ~24 s, o gerador acelera a voz levemente (sem mudar o tom) para caber nos 25 s.

Gerar: `VOZ=arquivo:/caminho/da/pasta python3 gerar_fatos.py fatos_minecraft_2026.mp4`
