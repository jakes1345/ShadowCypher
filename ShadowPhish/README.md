
# 🕵️‍♂️ ShadowPhish - APT Awareness Toolkit

**Version:** 1.0  
**Author:** Joas A Santos

> Visual simulator for cybersecurity awareness, phishing, and APT-based social engineering.

![image](https://github.com/user-attachments/assets/7fb46c48-f000-4e6e-832b-3a73e40c9508)

---

## 🔥 Features

- ✅ Malicious PDF generator
- ✅ Word macro with remote shellcode
- ✅ PowerShell obfuscation (Base64, IEX, compression, variables)
- ✅ Remote VBS + embedded HTTP server
- ✅ Prebuilt phishing websites (.sites/)
- ✅ Fake Recaptcha (Pasteshadow_operator style)
- ✅ Deepfake video (FaceFusion) and DeepVoice TTS
- ✅ Payload generator for Windows, Linux, macOS
- ✅ Built-in reverse shell listener with command interface
- ✅ APT Chains (APT29, APT41, FIN7)
- ✅ Smishing (SMS) and Vishing (voice call via Twilio)
- ✅ Malicious LNK shortcut builder
- ✅ HTML Smuggling generator (Base64 embedded)
- ✅ Simulated Ransomware + Decryptor
- ✅ QR Code phishing generator

---

## ⚙️ Requirements

- Python 3.10+
- PHP (for phishing sites)
- GCC / MinGW
- ffmpeg + facefusion
- Internet access (for DeepVoice and APIs)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run

```bash
python main.py
```

- Animated splash screen will appear
- Choose your language
- Toolkit interface will load

---

## 📁 Project Structure

```
.
├── main.py
├── backend/           # Main logic
├── frontend/          # Splash + language selector
├── .sites/            # Phishing templates
├── .fake-recaptcha/   # Fake Recaptcha pasteshadow_operator
├── outputs/           # Generated files
├── i18n/              # Translations
└── requirements.txt
```
---
## 🚀 Future Work & Improvements
- Multi-language support: Extend full translation coverage across all features and tooltips, with community-contributed language packs.
- Integrated reporting system: Generate PDF/HTML reports from simulations for audits, training, or awareness tracking.
- User role system: Introduce user roles (admin, operator, trainee) for multi-user environments.
- Phishing campaign builder: Visual editor to simulate full phishing campaigns with delivery scheduling and tracking.
- Cloud integration: Deploy phishing and payload simulations on isolated cloud environments for remote demonstrations.
- EDR/AV evasion lab: Create a module that benchmarks payload detection across common security solutions.
- Simulation scoring system: Automatically evaluate success or failure of simulated APT chains for gamification and training purposes.
- Plugin SDK: Allow developers to create and integrate custom payloads, phishing templates, or attack vectors.

---

## 🙏 Credits

- Developed by [Joas A Santos](https://www.linkedin.com/in/joas-antonio-dos-santos/)
- `.sites/` templates inspired and adapted from [Zphisher](https://github.com/htr-tech/zphisher)

---

## ⚠️ Legal Notice

> This toolkit is **strictly for educational and awareness purposes** only.  
> Do **not use** in real environments without **explicit authorization**.


---

# 🕵️‍♂️ ShadowPhish - APT Awareness Toolkit

**Versão:** 1.0  
**Autor:** Joas A Santos

> Simulador visual para conscientização sobre APTs, phishing, engenharia social e ameaças cibernéticas.

![image](https://github.com/user-attachments/assets/73703fcb-8dd6-47b1-9e02-4f4f8adf7bb9)

---

## 🔥 Funcionalidades

- ✅ Geração de PDFs maliciosos
- ✅ Macros Word com shellcode remoto
- ✅ PowerShell evasivo com opções de codificação, compressão e IEX
- ✅ VBS remoto com shellcode + servidor embutido
- ✅ Sites de phishing prontos (.sites/)
- ✅ Recaptcha Falso (Pasteshadow_operator)
- ✅ Deepfake (FaceFusion) e DeepVoice (TTS)
- ✅ Geração de Payload C2 para Windows, Linux e macOS
- ✅ Terminal interativo com listener embutido
- ✅ Cadeias de ataque APT29, APT41, FIN7
- ✅ Smishing (SMS) e Vishing (ligação com áudio)
- ✅ Gerador de LNK malicioso
- ✅ HTML Smuggling (base64 + download automático ou por clique)
- ✅ Simulador de Ransomware e Decryptor
- ✅ Geração de QR Code malicioso

---

## ⚙️ Requisitos

- Python 3.10+
- PHP (para servidores de phishing)
- GCC / MinGW
- ffmpeg + facefusion (para deepfake)
- Internet (para TTS, APIs)

Instale as dependências:
```bash
pip install -r requirements.txt
```

---

## 🚀 Como usar

```bash
python main.py
```

- Uma splash screen será exibida
- Selecione o idioma desejado
- A interface principal será carregada

---

## 📁 Estrutura

```
.
├── main.py
├── backend/           # Código principal
├── frontend/          # Splash + seletor de idioma
├── .sites/            # Templates de phishing
├── .fake-recaptcha/   # Recaptcha falso com payload automático
├── outputs/           # Arquivos gerados
├── i18n/              # Traduções em JSON
└── requirements.txt
```
---

## 🚀 Futuro & Melhorias
- Suporte multilíngue: Expandir a cobertura de tradução para todas as funcionalidades e dicas, com pacotes de idiomas contribuídos pela comunidade.
- Sistema de relatórios integrado: Gerar relatórios em PDF/HTML a partir das simulações para auditorias, treinamentos ou registros.
- Sistema de perfis de usuário: Introduzir papéis como administrador, operador e aprendiz para ambientes multiusuário.
- Construtor de campanhas de phishing: Editor visual para simular campanhas de phishing completas com agendamento de entrega e rastreamento.
- Integração com nuvem: Possibilidade de simular phishing e cargas maliciosas em ambientes de nuvem isolados para demonstrações remotas.
- Laboratório de evasão EDR/AV: Módulo que testa a detecção dos payloads em soluções de segurança populares.
- Sistema de pontuação de simulação: Avaliação automática de sucesso ou falha das cadeias APT para gamificação e treinamentos.
- SDK para Plugins: Permitir que desenvolvedores criem e integrem payloads, templates de phishing ou vetores de ataque personalizados.

---

## 🙏 Créditos

- Desenvolvido por [Joas A Santos](https://www.linkedin.com/in/joas-antonio-dos-santos/)
- Templates `.sites/` extraídos e adaptados do excelente projeto [Zphisher](https://github.com/htr-tech/zphisher)

---

## ⚠️ Aviso Legal

> Esta ferramenta é **estritamente educacional**, voltada para **conscientização e simulações** de segurança ofensiva.  
> **Não utilize em ambientes reais sem autorização.**

---
