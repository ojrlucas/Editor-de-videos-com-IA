#!/usr/bin/env bash
# Baixa as texturas reais do Minecraft (extraídas do jogo; propriedade da Mojang) usadas nos vídeos.
# Fonte: https://github.com/PrismarineJS/minecraft-assets
set -euo pipefail
cd "$(dirname "$0")"
tmp=$(mktemp -d); V=data/1.20.2
GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 --filter=blob:none --sparse https://github.com/PrismarineJS/minecraft-assets "$tmp/a"
git -C "$tmp/a" sparse-checkout set --no-cone /$V/entity/creeper/ /$V/entity/enderman/ /$V/entity/pig/ \
  /$V/items/{diamond,gold_ingot,emerald,gunpowder,ender_pearl,ender_eye}.png \
  /$V/blocks/{grass_block_side,grass_block_top,dirt,diamond_ore}.png
mkdir -p assets/minecraft; A="$tmp/a/$V"
cp $A/entity/creeper/creeper.png assets/minecraft/skin_creeper.png
cp $A/entity/enderman/enderman.png assets/minecraft/skin_enderman.png
cp $A/entity/enderman/enderman_eyes.png assets/minecraft/skin_enderman_eyes.png
cp $A/entity/pig/pig.png assets/minecraft/skin_pig.png
for f in diamond gold_ingot emerald gunpowder ender_pearl ender_eye; do cp $A/items/$f.png assets/minecraft/item_$f.png; done
for f in grass_block_side grass_block_top dirt diamond_ore; do cp $A/blocks/$f.png assets/minecraft/block_$f.png; done
W=data/26.1
git -C "$tmp/a" sparse-checkout set --no-cone /$W/items/{allay,copper_golem,creaking,happy_ghast}_spawn_egg.png \
  /$W/blocks/{golden_dandelion,creaking_heart,copper_block,exposed_copper,weathered_copper,oxidized_copper}.png \
  /$W/blocks/dried_ghast_hydration_0_{top,north,east}.png
B="$tmp/a/$W"
for f in allay copper_golem creaking happy_ghast; do cp $B/items/${f}_spawn_egg.png assets/minecraft/egg_$f.png; done
cp $B/blocks/golden_dandelion.png assets/minecraft/block_golden_dandelion.png
cp $B/blocks/creaking_heart.png assets/minecraft/block_creaking_heart.png
for f in copper_block exposed_copper weathered_copper oxidized_copper; do cp $B/blocks/$f.png assets/minecraft/block_$f.png; done
for f in top north east; do cp $B/blocks/dried_ghast_hydration_0_$f.png assets/minecraft/dried_ghast_$f.png; done
rm -rf "$tmp"; echo "ok: assets/minecraft"
