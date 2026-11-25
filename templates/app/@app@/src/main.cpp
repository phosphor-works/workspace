// SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
// SPDX-License-Identifier: GPL-3.0-or-later

#include <@AppNs@Core/Version.h>

#include <QCommandLineParser>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QtQml/QQmlExtensionPlugin>

Q_IMPORT_QML_PLUGIN(@AppNs @Plugin)

int main(int argc, char *argv[]) {
  QGuiApplication app(argc, argv);
  QGuiApplication::setApplicationName(QStringLiteral("@app@"));
  QGuiApplication::setApplicationDisplayName(QStringLiteral("@AppName@"));
  QGuiApplication::setApplicationVersion(@AppNs @Core::version());
  QGuiApplication::setDesktopFileName(QStringLiteral("@APPID@"));

  QCommandLineParser parser;
  parser.addHelpOption();
  parser.addVersionOption();
  parser.process(app);

  QQmlApplicationEngine engine;
  QObject::connect(
      &engine, &QQmlApplicationEngine::objectCreationFailed, &app,
      [] { QCoreApplication::exit(1); }, Qt::QueuedConnection);
  engine.loadFromModule("@AppNs@", "Main");
  return QGuiApplication::exec();
}
