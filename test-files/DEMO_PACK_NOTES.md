# Demo Pack Notes

The generated sample pack under `test-files/e2e-demo-pack/` is designed to exercise the app end to end:

- one campaign brief in both PDF and DOCX form
- multiple channel assets in upload-ready PDF/DOCX form
- a mix of aligned and intentionally misaligned copy so the QA stage has visible output

Regenerate the files with:

```bash
/home/shridhar_shubham/cnd-capstone/campaign-intelligence/.venv/bin/python /home/shridhar_shubham/cnd-capstone/campaign-intelligence/test-files/create_e2e_demo_pack.py
```