#pragma once
#include <QWidget>

class FinishPage : public QWidget {
    Q_OBJECT
public:
    explicit FinishPage(bool success, QWidget* parent = nullptr);
};
