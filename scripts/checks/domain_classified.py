import sys, yaml, pathlib
prefix = sys.argv[1]
m = yaml.safe_load(open('config/capability-manifest.yaml'))['capabilities']
declared = {v.get("delegate_skill","").replace("sweetclaude:","") for v in m.values() if v.get("delegate_skill")}
skills = sorted(p.parent.name for p in pathlib.Path("skills").glob("*/SKILL.md")
                if p.parent.name.startswith(prefix))
missing = [s for s in skills if s not in declared]
print(f"{prefix}: {len(skills)} skills, {len(skills)-len(missing)} classified, {len(missing)} unclassified")
if missing:
    print("unclassified:", ", ".join(missing)); sys.exit(1)
