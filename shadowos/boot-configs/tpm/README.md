# TPM 2.0

Notes for measured boot, IMA/EVM and sealing keys to a TPM 2.0 chip. Nothing in the build or installer uses these files; see [`../README.md`](../README.md).

## Files

- `boot.conf`: TPM device, the PCRs to use, IMA/EVM switches, an attestation server and NV indices. The attestation server (`shadowcypher-attestation.local:9090`) is a placeholder; ShadowCypher doesn't run one.
- `kernel-params.txt`: IMA and EVM settings, module signature enforcement, kernel lockdown, AppArmor and memory-hardening options.

## Problems in `kernel-params.txt`

- `nokaslr` disables kernel address randomization, and `efi=noruntime` disables EFI runtime services.
- `tpm_crb=force`, `tpm_tis=force`, `tpm2_eventlog=enable`, `ima=enforce`, `evm=enforce`, `evm_x509_path`, `evm_ignore_errors`, `efivarfs=secure`, `tpm_crb.log_level` and the `dm_verity.*` lines aren't kernel parameters.
- `kernel.kptr_restrict=3` is out of range (0 to 2). The `kernel.*` lines are sysctls anyway.
- `ima_appraise=enforce` plus `lockdown=integrity` and `module.sig_enforce=1` will stop the system from booting unless files are labeled and every module is signed, including out-of-tree ones such as NVIDIA's.

## What the image has

The ISO includes `tpm2-tools` and `cryptsetup`. On an installed system, `systemd-cryptenroll --tpm2-device=auto` can bind a LUKS volume to the TPM, which covers the usual "unlock the disk only if the boot chain is unchanged" case without IMA or EVM. Useful checks:

```bash
ls /dev/tpm*
cat /sys/class/tpm/tpm0/tpm_version_major
tpm2_pcrread sha256
```

## References

- Trusted Computing Group: https://trustedcomputinggroup.org/
- tpm2-tools: https://github.com/tpm2-software/tpm2-tools
- `man systemd-cryptenroll`
