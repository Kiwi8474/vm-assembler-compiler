# MX-Technologies: Overview

---

## 0. Table of Contents
- [1\. Corporate Mission](#1-corporate-mission)
- [2\. The MX-Nomenclature](#2-the-mx-nomenclature)
- [3\. Core Architecture (MX-26101)](#3-core-architecture-mx-26101)
- [4\. System Deployment](#4-system-deployment)
    - [4.1 Compilation](#41-compilation)
    - [4.2 Graphics Subsystem](#42-graphics-subsystem)
    - [4.3 Automated Boot](#43-automated-boot)

---

## 1. Corporate Mission
MX-Technologies is dedicated to the development of high-performance virtual environments. Our goal is to provide a clean, register-based architecture that bridges the gap between low-level hardware control and modern execution speed.

## 2. The MX-Nomenclature
All CPU models within our ecosystem follow the standardized MX-naming convention:
- **MX:** Official corporate brand identifier.
- **26:** Static prefix.
- **1:** Generation/Serial number (e.g., 1 for initial series).
- **01:** Designated core count of the processing unit.

## 3. Core Architecture
- [**MX-26101**](https://github.com/Kiwi8474/vm-assembler-compiler/blob/main/docs/MX-26101.md)

## 4. System Deployment
To maintain peak execution speeds, the virtual machines must be compiled with hardware-native optimizations.

### 4.1 Compilation
```g++ -O3 -march=native main.cpp -o vm.exe```

### 4.2 Graphics Subsystem
The visual output is handled by a dedicated Python-based engine via shared memory.

### 4.3 Automated Boot
To boot the virtual machine alongside with the graphics engine at the same time, we recommend to use the given batch file.
```.\start.bat```

---

### MX-Technologies Inc. | R&D Division | Lead Architect: [Kiwi8474](https://github.com/Kiwi8474)