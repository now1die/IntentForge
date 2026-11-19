"""Original Mini-C exercise implementations and hand-selected fault locations."""
import argparse
import json
from pathlib import Path

from .corpus import DATA

DEVELOPMENT = DATA / "ml-v3-development-v1.json"
FINAL = DATA / "ml-v3-final-v1.json"


def repair(family, category, reference, correct, faulty, *, kind="compiler", natural=None, explicit=None):
    if reference.count(correct) != 1:
        raise ValueError(f"{family}: repair anchor must be unique")
    return {"id": family, "family": family, "category": category, "kind": kind,
            "source": reference.replace(correct, faulty, 1), "accepted": [reference],
            "provenance": "Original IntentForge Mini-C exercise and authored fault",
            **({"natural": natural, "explicit": explicit} if natural and explicit else {})}


def control(family, source, ambiguous=False):
    return {"id": family, "family": family, "category": "AMBIGUOUS" if ambiguous else "VALID_CONTROL",
            "kind": "control", "source": source, "accepted": [], "ambiguous": ambiguous,
            "provenance": "Original IntentForge Mini-C exercise"}


V, A, D, F, M = "VARIABLE_REFERENCE", "ARRAY_INDEX", "DECLARATION_TYPE", "FUNCTION_ARGUMENT", "MISSING_EXPRESSION"
C, R, O, X = "COMPARISON_OPERATOR", "RETURN_EXPRESSION", "ARITHMETIC_OPERATOR", "MULTIPLE_LOCALIZED"
L = {"kind": "logic"}

PARTITIONS = {
"train": [
    repair("ribbon_area", V, "int cut(int width,int tall,int waste){ if(width<=waste){return 0;} int floor=width-waste; return floor*tall; }", "floor*tall", "flor*tall"),
    repair("reverse_emit", A, "int tiles[12]; int emit(int n){int sum=0; while(n>0){int back=n-1; sum+=tiles[back];n--;} return sum;}", "tiles[back]", "tiles[bak]"),
    repair("stamp_credit", D, "bool claim(int coins,int cap){bool allowed=coins>=cap; {int coins=cap-1;if(coins<0){return false;}} bool paid=allowed;return paid;}", "paid=allowed", "paid=cap"),
    repair("panel_transform", F, "float shade(float lux,bool matte,int levels){ if(matte){return lux/levels;}return lux;} float paint(int tick,float lux,bool matte){return shade(lux,matte,tick);}", "shade(lux,matte,tick)", "shade(matte,tick,lux)"),
    repair("checksum_cycle", M, "int checksum(int n,int seed){int hash=seed; for(int i=0;i<n;i++){hash=(hash+i)%7;} return hash;}", "return hash;", "return;"),
    repair("slice_width", V, "int yband=3; int height(int row,int baseline){if(row<baseline){return 0;} int dist=row-yband; if(dist<0){return 0;} return dist;}", "return dist", "return dst"),
    repair("stage_lookup", A, "int stage[7]; int seek(int after){for(int slot=after;slot<7;slot++){if(stage[slot]==0){return slot;}}return -1;}", "stage[slot]", "stage[slt]"),
    repair("route_metric", F, "int weight(int meters,bool icy){if(icy){return meters*2;}return meters;} int walk(int blocks,bool frost,int detour){int meters=blocks+detour;return weight(meters,frost);}", "weight(meters,frost)", "weight(meters,frst)"),
    repair("gate_clear", D, "bool flag(int state,bool manual){bool not_busy=state!=1; if(manual){return true;}bool permitted=not_busy;return permitted && state>0;}", "permitted=not_busy", "permitted=state"),
    repair("grid_sum", M, "int grid[9]; int sumgrid(){int total=0;for(int row=0;row<3;row++){for(int col=0;col<3;col++){total+=grid[row*3+col];}}return total;}", "return total;", "return;"),
    repair("peak_balance", V, "float adjust(float step,int height){float local=step+height; float level=step-height; if(level>local){return local;} return level;}", "return level", "return lvel"),
    repair("read_window", A, "int buf[8]; int mid(int high,int low){int middle=(high+low)/2; if(middle>7){return 0;} return buf[middle];}", "buf[middle]", "buf[midle]"),
    repair("claim_bucket", X, "int slots[5]; int book(int row){int next=row+1;slots[next]=row;return slots[next]+row;}", "return slots[next]+row", "return slots[nxt]+rw"),
    repair("message_tag", F, "int style(bool loud,int rank,char prefix){if(loud){return rank+1;}return rank;} int title(int level,char tag,bool noise){return style(noise,level,tag);}", "style(noise,level,tag)", "style(tag,noise,level)"),
    repair("remainder_weight", R, "int last(int a,int b,bool first){int rem=a%b; if(first){return rem;} return rem;}", "} return rem;", "} return a;", **L),
    repair("sensor_floor", C, "int measures[6]; int mark(){for(int key=0;key<6;key++){measures[key]=key;}return 0;}", "key<6", "key<=6", **L),
    repair("cost_layers", O, "int layers(int s,int t,int u,int base){int w=s*base;int x=t*base;int y=u*base;return w+x+y;}", "u*base", "u+base", **L),
    repair("label_width", V, "int box(int text,int pad,bool snug){int outer=text+pad; if(snug){outer-=pad;} else {outer+=1;} return outer;}", "return outer", "return outr"),
    repair("track_diff", V, "int last=0; int tick(int next){int delta=next-last;last=next;if(delta<0){delta=-delta;}return delta;}", "return delta;", "return dlt;"),
    repair("inventory_line", F, "int unit_cost(int amount,int rebate,bool active){if(active){return amount-rebate;}return amount;} int due(int price,int token,bool active){int discounted=token/2;return unit_cost(price,discounted,active);}", "unit_cost(price,discounted,active)", "unit_cost(price,disconted,active)"),
    repair("fold_order", A, "int input[8]; int read(int half,bool original){int high=7-half;if(original){return input[half];}return input[high];}", "input[high]", "input[hg]"),
    repair("even_relays", D, "bool relay(int incoming,int step){bool even=incoming%2==0;while(step>0){step--;} {bool flip=even; if(!flip){return false;}}bool send=even;return send;}", "send=even", "send=step"),
    repair("block_budget", M, "int tax(int goal,int spare){int debt=goal; if(goal>spare){debt-=spare;} else {debt+=spare;} return debt;}", "return debt;}", "return;}"),
    repair("cross_widths", X, "int pack(int first,int last,bool vertical){int low=first-1;int high=last+1; if(vertical){return high;} return high-low;}", "return high-low", "return hig-lo"),
    repair("pitch_guess", F, "float pitch(bool boost,float hz,int base){if(boost){return hz+base;}return hz;}float tone(float hz,bool sharp,int offset){return pitch(sharp,hz,offset);}", "pitch(sharp,hz,offset)", "pitch(offset,sharp,hz)"),
    control("control_preparation", "int allocate(int rooms,int width){if(width<0){return -1;} int possible=rooms*width; rooms++;return rooms;}"),
    control("control_index_guard", "int cards[3]; int deck(){for(int i=0;i<=3;i++){if(i==3){break;} cards[i]=i;}return cards[2];}"),
],
"selection": [
    repair("signal_ring", A, "int queue[9]; int signal(int pos){if(pos<0){return 0;} int mod=pos%9; return queue[mod];}", "queue[mod]", "queue[md]"),
    repair("temperature_trip", V, "float trip(int retry,float heat){float threshold=heat+1;while(retry>0){heat+=2;retry--;}return threshold-heat;}", "threshold-heat", "threshld-heat"),
    repair("count_flags", M, "int chosen(bool keep,int passes){int rounds=0;while(keep && passes>0){rounds+=1;passes--;} return rounds;}", "return rounds;", "return;"),
    repair("safety_override", D, "bool allow(bool override,int density){bool crowded=density>5; bool safe=override; if(crowded){return safe;} return !crowded;}", "safe=override", "safe=density"),
    repair("route_tag", F, "int locate(bool ready,char name,float rate){if(ready){return 1;}return 0;} int location(char label,float drift,bool tracking){return locate(tracking,label,drift);}", "locate(tracking,label,drift)", "locate(drift,tracking,label)"),
    repair("net_turn", V, "int score(int goal,int debt){int net=goal-debt;{int goal=net;if(goal<0){return -1;}}return net;}", "return net;", "return nt;"),
    repair("seat_mask", F, "bool active(int seat,bool on){return on && seat>=0;} bool check(int n,bool local){int center=n/2;return active(center,local);}", "active(center,local)", "active(cener,local)"),
    repair("streak_longest", M, "int best(int run,int peak){while(run>peak){peak++;} if(peak>0){peak*=2;}return peak;}", "return peak;", "return;"),
    repair("landing_table", C, "int pads[5];int landing(){for(int j=0;j<5;j++){pads[j]=j*2;}return pads[4];}", "j<5", "j<=5", **L),
    control("control_optional_mirror", "int sample(int input,int offset,bool check){int draft=input+offset;if(check){return draft;}return input;}"),
],
"calibration": [
    repair("capped_density", V, "float measure(float units,float time){float ratio=units/time; if(ratio>9){return 9;} return ratio;}", "return ratio;", "return rat;"),
    repair("weekday_palette", A, "int paint[7]; int hue(int packet){int cycle=packet%7; if(cycle<0){return -1;}return paint[cycle];}", "paint[cycle]", "paint[cycl]"),
    repair("queue_promote", M, "int promote(int late,int start){int head=start;for(int k=late;k>0;k--){if(head>10){break;}head++;}return head;}", "return head;", "return;"),
    repair("seal_notification", F, "bool can_send(char mark,bool live,int channel){return live && channel>0;} bool alert(int lane,char seal,bool armed){return can_send(seal,armed,lane);}", "can_send(seal,armed,lane)", "can_send(lane,seal,armed)"),
    repair("reset_latch", D, "bool latch(int amount,bool state){bool dropped=amount<0; bool saved=state;if(dropped){return false;}return saved;}", "saved=state", "saved=amount"),
    repair("stairs_choice", V, "int stairs(int one,int three,int bonus){int chosen=three+bonus; if(one>chosen){return one;} return chosen;}", "return chosen", "return chsen"),
    repair("safety_pad", C, "int route[10];int collect(){int x=0;for(int k=0;k<10;k++){x=route[k];}return x;}", "k<10", "k<=10", **L),
    control("control_asymmetric_prices", "int cost(int peak,int valley,int tax){int a=peak*tax;int b=valley*tax;if(b<0){return 0;}int c=peak+tax;return a+b+c;}"),
],
"development": [
    repair("sampling_tail", A, "int visits[4];int gather(int seed){if(seed<0){return 0;}for(int slot=0;slot<4;slot++){int current=visits[slot];seed+=current;}return seed;}", "visits[slot];", "visits[slot+1];", **L),
    repair("scale_format", F, "float scale(char token,float power,bool show){if(show){return power;}return 0;}float formatted(bool draw,char point,float n){return scale(point,n,draw);}", "scale(point,n,draw)", "scale(n,draw,point)"),
    repair("batch_stamps", V, "int stamps(int count,int multiplier){int collected=count*multiplier;while(count>1){count--;}return collected;}", "return collected", "return colleced"),
    repair("packing_array", A, "int rack[4]; int get(int at){return rack[at];}", "rack[at]", "rack[0]", natural={"description":"return the element of rack at index at"}, explicit={"return_expression":"rack[at]"}, **L),
    control("control_intentional_audit", "int settle(int subtotal,int tax){int gross=subtotal+tax; if(gross>100){return 0;} return subtotal;}"),
    control("ambiguous_panel", "int choose(int active,int alternate){if(active>alternate){return selected;}return active;}", True),
],
}


def build():
    cases = []
    for split, partition in PARTITIONS.items():
        for record in partition:
            cases.append({**record, "split": split})
    return {"version": 1, "cases": cases}


def read(path):
    return json.loads(Path(path).read_text())["cases"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEVELOPMENT)
    target = parser.parse_args().out
    target.write_text(json.dumps(build(), indent=2) + "\n")
