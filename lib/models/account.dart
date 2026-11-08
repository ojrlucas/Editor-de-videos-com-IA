import 'package:flutter/material.dart';

const accountColors = [
  Color(0xFF4F46E5),
  Color(0xFF0D9488),
  Color(0xFFDB2777),
  Color(0xFFEA580C),
  Color(0xFF2563EB),
  Color(0xFF65A30D),
];

class Account {
  final String id;
  String name;
  int color;

  Account({required this.id, required this.name, this.color = 0});

  Color get tint => accountColors[color % accountColors.length];
  String get initial => name.trim().isEmpty ? '?' : name.trim()[0].toUpperCase();

  Map<String, dynamic> toJson() => {'id': id, 'name': name, 'color': color};
  factory Account.fromJson(Map<String, dynamic> j) => Account(
      id: j['id'] as String,
      name: j['name'] as String,
      color: j['color'] as int? ?? 0);
}
