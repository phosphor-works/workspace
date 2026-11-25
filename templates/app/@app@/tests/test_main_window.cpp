// SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
// SPDX-License-Identifier: GPL-3.0-or-later

#include <QQmlApplicationEngine>
#include <QQuickWindow>
#include <QTest>
#include <QtQml/QQmlExtensionPlugin>

Q_IMPORT_QML_PLUGIN(@AppNs @Plugin)

class TestMainWindow : public QObject {
  Q_OBJECT

private Q_SLOTS:
  void theWindowLoadsWithTheAppName() {
    QGuiApplication::setApplicationDisplayName(QStringLiteral("@AppName@"));
    QQmlApplicationEngine engine;
    engine.loadFromModule("@AppNs@", "Main");
    QCOMPARE(engine.rootObjects().size(), 1);
    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().first());
    QVERIFY(window);
    QCOMPARE(window->title(), QStringLiteral("@AppName@"));
  }
};

QTEST_MAIN(TestMainWindow)
#include "test_main_window.moc"
