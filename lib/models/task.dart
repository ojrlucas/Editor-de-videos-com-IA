enum TaskPriority { low, medium, high }

extension TaskPriorityX on TaskPriority {
  String get label => switch (this) {
        TaskPriority.low => 'Baixa',
        TaskPriority.medium => 'Média',
        TaskPriority.high => 'Alta',
      };
}

class SubTask {
  String title;
  bool done;
  SubTask(this.title, {this.done = false});

  Map<String, dynamic> toJson() => {'title': title, 'done': done};
  factory SubTask.fromJson(Map<String, dynamic> j) =>
      SubTask(j['title'] as String, done: j['done'] as bool? ?? false);
}

const defaultCategories = [
  'Pessoal',
  'Trabalho',
  'Estudos',
  'Saúde',
  'Casa',
  'Finanças',
];

class Task {
  int id;
  String title;
  String notes;
  DateTime due;
  TaskPriority priority;
  String category;
  List<SubTask> subtasks;

  /// Minutos antes do prazo em que uma notificação normal é disparada (0 = no horário).
  List<int> reminders;

  /// Se true, dispara o alerta estilo "ligação" [callMinutes] minutos antes.
  bool callAlert;
  int callMinutes;

  bool done;
  DateTime? doneAt;
  DateTime createdAt;

  Task({
    required this.id,
    required this.title,
    this.notes = '',
    required this.due,
    this.priority = TaskPriority.medium,
    this.category = 'Pessoal',
    List<SubTask>? subtasks,
    List<int>? reminders,
    this.callAlert = true,
    this.callMinutes = 10,
    this.done = false,
    this.doneAt,
    DateTime? createdAt,
  })  : subtasks = subtasks ?? [],
        reminders = reminders ?? [],
        createdAt = createdAt ?? DateTime.now();

  bool get isOverdue => !done && due.isBefore(DateTime.now());

  double get progress {
    if (subtasks.isEmpty) return done ? 1 : 0;
    return subtasks.where((s) => s.done).length / subtasks.length;
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'notes': notes,
        'due': due.toIso8601String(),
        'priority': priority.index,
        'category': category,
        'subtasks': subtasks.map((s) => s.toJson()).toList(),
        'reminders': reminders,
        'callAlert': callAlert,
        'callMinutes': callMinutes,
        'done': done,
        'doneAt': doneAt?.toIso8601String(),
        'createdAt': createdAt.toIso8601String(),
      };

  factory Task.fromJson(Map<String, dynamic> j) => Task(
        id: j['id'] as int,
        title: j['title'] as String,
        notes: j['notes'] as String? ?? '',
        due: DateTime.parse(j['due'] as String),
        priority: TaskPriority.values[j['priority'] as int? ?? 1],
        category: j['category'] as String? ?? 'Pessoal',
        subtasks: (j['subtasks'] as List? ?? [])
            .map((e) => SubTask.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
        reminders: (j['reminders'] as List? ?? []).cast<int>(),
        callAlert: j['callAlert'] as bool? ?? true,
        callMinutes: j['callMinutes'] as int? ?? 10,
        done: j['done'] as bool? ?? false,
        doneAt:
            j['doneAt'] == null ? null : DateTime.parse(j['doneAt'] as String),
        createdAt: DateTime.parse(j['createdAt'] as String),
      );
}
