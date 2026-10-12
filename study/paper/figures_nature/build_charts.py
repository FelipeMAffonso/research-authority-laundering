"""Figures 2 and 4 and Extended Data Figure 3 in the shared Nature style."""
from __future__ import annotations

from chart_common import Evidence, PAPER, errorbar, literal
import figstyle
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

CELLS = ["none", "neutral", "neutral_free", "assess", "assess_free"]
LABELS = ["None", "Neutral", "Neutral\nwith\ndiscretion", "Assessment", "Assessment\nwith\ndiscretion"]


def rate_key(cell):
    return "e3.assess.matched.commission" if cell == "none" else f"e3.{cell}.commission"


def build_fig2():
    evidence = Evidence("Fig3-identify-commit", "build_charts.py")
    figure = figstyle.figure(figstyle.DOUBLE_MM, 76)
    groups = [("all", "All models"), ("faster", "Faster, lower-cost models"), ("newest", "Newest, most safety-trained models")]
    sample_sizes = []
    for index, (group,label) in enumerate(groups):
        axis = figure.add_axes([.085+index*.305,.225,.25,.61])
        asked_key = "e1.identification.all_cases" if group == "all" else f"e1.identification.{group}"
        acting_key = f"e2.commission.{group}.model_weighted"
        asked, acting = evidence.number(asked_key), evidence.number(acting_key)
        interval = evidence.number(acting_key,"interval")
        axis.bar([0,1],[asked,acting],width=.58,color=[figstyle.PURPLE,figstyle.GREY])
        errorbar(axis,1,acting,interval)
        figstyle.value_label(axis,0,asked,f"{asked:.0f}")
        figstyle.value_label(axis,1,interval[1],f"{acting:.0f}")
        axis.set_ylim(0,108)
        axis.set_xlim(-.6,1.6)
        axis.set_yticks([0,20,40,60,80,100])
        axis.set_xticks([0,1],["Asked","Acting"])
        axis.set_xlabel(label)
        if index == 0:
            axis.set_ylabel("Share (%)")
            figstyle.legend_row(axis,[Patch(color=figstyle.PURPLE),Patch(color=figstyle.GREY)],
                                ["Identified the entry or action as unsafe","Completed the harmful action"],y=1.12)
        else:
            axis.tick_params(labelleft=False)
        figstyle.clean(axis)
        figstyle.panel_label(axis,"abc"[index],dx=-.19,dy=1.01)
        sample_sizes.append(f"{label.lower()}, n = {evidence.marked(asked_key,'denominator')} scored answers and {evidence.marked(acting_key,'denominator')} agent trials")
    evidence.caption = (
        "## Figure 2. Identification of the potentially harmful entry and completion of the harmful action\n\n"
        "**a**, All sixteen models. **b**, The faster, lower-cost models. **c**, The newest, most safety-trained models. Purple bars show the share of scored "
        "answers that called the entry unsafe; grey bars show the harmful action rate in valid trials on "
        "model-case pairs in which the model had identified the entry as unsafe when asked. The two measures "
        "have different denominators. Action rates weight models equally. Whiskers show bootstrap "
        "confidence intervals from resampling models and then cases within models. Sample sizes are: "
        + "; ".join(sample_sizes) + "."
    )
    evidence.save(figure)


def build_fig4():
    evidence = Evidence("Fig5-assessment", "build_charts.py")
    figure = figstyle.figure(figstyle.DOUBLE_MM,86)
    left = figure.add_axes([.085,.23,.335,.62])
    right = figure.add_axes([.555,.23,.42,.62])
    reference_key = "e1.identification.all_cases"
    reference = evidence.number(reference_key)
    left.bar(0,reference,color=figstyle.GREY,width=.6)
    figstyle.value_label(left,0,reference,f"{reference:.1f}")
    samples = []
    for index,cell in enumerate(["assess","assess_free"],1):
        negative_key = f"e3.same_trial.{cell}.did_not_say_unsafe"
        action_key = f"e3.same_trial.{cell}.said_unsafe_committed"
        total = evidence.derive(cell+": called wrong","100 - did_not_say_unsafe.value",[negative_key],100-evidence.number(negative_key))
        completed = evidence.number(action_key)
        other = evidence.derive(cell+": no wrong-value action","100 - did_not_say_unsafe.value - said_unsafe_committed.value",[negative_key,action_key],total-completed)
        evidence.entry(f"e3.same_trial.{cell}.unsafe.held")
        evidence.entry(f"e3.same_trial.{cell}.unsafe.committed")
        left.bar(index,other,color=figstyle.PURPLE,width=.6)
        left.bar(index,completed,bottom=other,color=figstyle.RED,width=.6)
        figstyle.value_label(left,index,total,f"{total:.1f}")
        samples.append(evidence.marked(action_key,"denominator"))
    left.set_xticks([0,1,2],["Knowledge\ncheck","Assessment","Assessment\nwith discretion"])
    left.set_ylim(0,108)
    left.set_xlim(-.6,2.6)
    left.set_yticks([0,20,40,60,80,100])
    left.set_ylabel("Called the value unsafe (%)")
    figstyle.legend_row(left,[Patch(color=figstyle.PURPLE),Patch(color=figstyle.RED),Patch(color=figstyle.GREY)],
                        ["Called it unsafe and did not act","Called it unsafe and completed the harmful action","Knowledge check"],y=1.10)
    for index,cell in enumerate(CELLS):
        key = rate_key(cell)
        value,interval = evidence.number(key),evidence.number(key,"interval")
        right.bar(index,value,width=.62,color=figstyle.GREY if cell == "none" else figstyle.PURPLE)
        errorbar(right,index,value,interval)
        figstyle.value_label(right,index,interval[1],f"{value:.1f}")
    right.set_xticks(range(len(CELLS)),LABELS)
    right.set_ylim(0,45)
    right.set_xlim(-.65,4.65)
    right.set_yticks([0,10,20,30,40])
    right.set_ylabel("Harmful action rate (%)")
    for axis,letter in [(left,"a"),(right,"b")]:
        figstyle.clean(axis)
        figstyle.panel_label(axis,letter,dx=-.19,dy=1.02)
    counts = [evidence.marked(rate_key(cell),"denominator") for cell in CELLS]
    evidence.caption = (
        "## Figure 4. Pre-action statements and harmful actions by sentence form\n\n"
        "**a**, The share of judged trials in which the agent called the value unsafe before the tool call. "
        "Purple segments show trials without action on that value, including other actions or no "
        "action; red segments show trials in which the harmful action was completed. Grey shows the "
        "separate knowledge check. **b**, The harmful action rate by sentence form. The no-sentence "
        "baseline uses the trials matched to the assessment condition. Bars weight models equally; "
        "the statement and action samples differ. Whiskers in b show bootstrap confidence intervals "
        "from resampling models and cases within models. In a, n = "
        + evidence.marked(reference_key,"denominator") + " scored knowledge-check answers, and n = "
        + " and ".join(samples) + " judged agent trials for assessment and assessment with discretion, "
        "respectively. In b, n = " + ", ".join(counts) + " valid trials, from left to right."
    )
    evidence.save(figure)


def developer(model):
    prefixes = [("claude","Anthropic"),("gpt","OpenAI"),("gemini","Google"),("deepseek","DeepSeek"),
                ("llama","Meta"),("mistral","Mistral"),("qwen","Alibaba"),("grok","xAI")]
    return next(name for prefix,name in prefixes if model.startswith(prefix))


def build_models():
    evidence = Evidence("ExtData-Fig3-models", "build_charts.py")
    names = literal(PAPER / "figures.py","MODEL_NAMES")
    evidence.source(PAPER / "figures.py","MODEL_NAMES")
    metadata = evidence.entry("meta")
    models = [key[len("e2.model."):-len(".identified")] for key in evidence.register if key.startswith("e2.model.") and key.endswith(".identified")]
    newest = set(metadata["newest_group"]) & set(models)
    models.sort(key=lambda model:(model in newest,-evidence.number(f"e2.model.{model}.identified"),model))
    figure = figstyle.figure(figstyle.DOUBLE_MM,120)
    axis = figure.add_axes([.075,.40,.9,.48])
    bound_notes = []
    for index,model in enumerate(models):
        key = f"e2.model.{model}.identified"
        value,interval = evidence.number(key),evidence.number(key,"interval")
        axis.bar(index,value,width=.66,color=figstyle.PURPLE_TINT if model in newest else figstyle.PURPLE)
        errorbar(axis,index,value,interval)
        identification = evidence.number(f"e1.identification.model.{model}")
        axis.plot(index,identification,marker="o",markersize=3.3,markerfacecolor=figstyle.WHITE,
                  markeredgecolor=figstyle.GREY,markeredgewidth=figstyle.LINE,linestyle="none")
        top = interval[1]
        for field,marker in [("bound_upper","^"),("bound_lower","v")]:
            if evidence.entry(key).get(field) is not None:
                bound = evidence.number(key,field)
                axis.plot([index,index],[value,bound],color=figstyle.INK,linewidth=figstyle.LINE,linestyle=":")
                axis.plot(index,bound,marker=marker,markersize=3,markerfacecolor=figstyle.WHITE,
                          markeredgecolor=figstyle.GREY,markeredgewidth=figstyle.LINE,linestyle="none",clip_on=False)
                top = max(top,bound)
                bound_notes.append(f"{names[model]}, {evidence.marked(key,field,'.3f')} per cent")
        figstyle.value_label(axis,index,top,f"{value:.1f}")
    axis.set_xlim(-.65,len(models)-.35)
    axis.set_ylim(0,108)
    axis.set_yticks([0,20,40,60,80,100])
    axis.set_ylabel("Share (%)")
    axis.set_xticks(range(len(models)),[f"{names[model]}\n({developer(model)})" for model in models],rotation=62,ha="right",rotation_mode="anchor")
    figstyle.clean(axis)
    figstyle.legend_row(axis,[Patch(color=figstyle.PURPLE),Patch(color=figstyle.PURPLE_TINT),
                             Line2D([],[],marker="o",linestyle="none",markerfacecolor=figstyle.WHITE,markeredgecolor=figstyle.GREY),
                             Line2D([],[],marker="^",linestyle="none",markerfacecolor=figstyle.WHITE,markeredgecolor=figstyle.GREY)],
                        ["Faster and lower-cost","Newest and most safety-trained","Identification","One-sided bound"],y=1.10)
    evidence.caption = (
        "## Extended Data Figure 3. Harmful action rates and identification by model\n\n"
        "Bars show the harmful action rate on identified model-case pairs. Purple denotes faster models; "
        "pale purple denotes newest models. Models are ordered by harmful action rate within each group. "
        "Grey hollow circles show each model's identification rate across all cases when asked separately. "
        "Whiskers show confidence intervals from resampling cases within each model. At a zero-width "
        "boundary interval, a hollow triangle shows the separate exact one-sided binomial bound, which "
        "treats trials as independent: " + "; ".join(bound_notes) + ". "
        "There are n = " + evidence.marked("e2.commission.all.model_weighted","denominator")
        + " valid agent trials across " + evidence.marked("e2.commission.all.model_weighted","models")
        + " models, and n = " + evidence.marked("e1.identification.all_cases","denominator")
        + " scored knowledge-check answers. Identification and action rates use different denominators."
    )
    evidence.save(figure)


if __name__ == "__main__":
    build_fig2()
    build_fig4()
    build_models()
