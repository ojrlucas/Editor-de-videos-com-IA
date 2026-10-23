import 'package:intl/intl.dart';

String minutesLabel(int m) {
  if (m == 0) return 'No horário';
  if (m % 1440 == 0) return '${m ~/ 1440} dia${m ~/ 1440 > 1 ? 's' : ''} antes';
  if (m % 60 == 0) return '${m ~/ 60} h antes';
  return '$m min antes';
}

String durationText(Duration d) {
  d = d.abs();
  if (d.inDays >= 1) {
    final h = d.inHours % 24;
    return h == 0 ? '${d.inDays} d' : '${d.inDays} d ${h} h';
  }
  if (d.inHours >= 1) {
    final m = d.inMinutes % 60;
    return m == 0 ? '${d.inHours} h' : '${d.inHours} h ${m} min';
  }
  if (d.inMinutes >= 1) return '${d.inMinutes} min';
  return 'instantes';
}

String relativeDue(DateTime due, {bool done = false}) {
  if (done) return DateFormat("d MMM · HH:mm", 'pt_BR').format(due);
  final diff = due.difference(DateTime.now());
  return diff.isNegative
      ? 'Atrasada há ${durationText(diff)}'
      : 'Vence em ${durationText(diff)}';
}

String fullDue(DateTime due) =>
    DateFormat("EEE, d 'de' MMM · HH:mm", 'pt_BR').format(due);

DateTime dayOnly(DateTime d) => DateTime(d.year, d.month, d.day);
