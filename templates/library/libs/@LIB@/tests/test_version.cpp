// SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
// SPDX-License-Identifier: LGPL-2.1-or-later

#include <@LIBTARGET@/Version.h>

#include <QTest>

class TestVersion : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void versionIsTheProjectVersion()
    {
        QCOMPARE(@LIBTARGET@::version(), QStringLiteral("0.1.0"));
    }
};

QTEST_GUILESS_MAIN(TestVersion)
#include "test_version.moc"
