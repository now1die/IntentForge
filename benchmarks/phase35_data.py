"""Original Mini-C programs for development and held-out policy evaluation."""
import json

from .corpus import DATA
from .ml_v3_data import A, C, D, F, M, V, control, repair

DEVELOPMENT = DATA / "phase35-development-v1.json"
FINAL = DATA / "phase35-final-v1.json"


def store(path, partitions):
    rows = [{**case, "split": split} for split, cases in partitions.items() for case in cases]
    path.write_text(json.dumps({"version": 1, "cases": rows}, indent=2) + "\n")


PARTITIONS = {
    "train": [
        repair("refund_branch", V, "int reimburse(int cost,int fee,bool credit){int net=cost-fee;while(net<0){net+=cost;}if(credit){return net+fee;}return net;}",
               "}return net;", "}return ne;"),
        repair("shade_grid", A, "int tiles[25];int shades(int col,int row){if(col>4){col=4;}int point=row*5+col;while(point<0){point+=5;}return tiles[point];}",
               "return tiles[point]", "return tiles[ponit]"),
        repair("mirror_charge", M, "int fill(int balance,int bill){for(int j=0;j<2;j++){if(bill<0){bill=-bill;}balance-=bill;}return balance;}",
               "return balance;", "return;"),
        repair("dry_plant", D, "bool grow(int rain,bool dry,int size){bool irrigate=rain<size;bool usable=dry;if(irrigate){return usable;}return rain>0;}",
               "usable=dry", "usable=size"),
        repair("bus_meter", F, "int fare(int hops,bool peak){if(peak){return hops*3;}return hops*2;} int ride(int start,int end,bool surge){int stops=end-start;if(stops<0){return 0;}return fare(stops,surge);}",
               "fare(stops,surge)", "fare(stps,surge)"),
        repair("volume_quota", V, "int total=0; int add(int request,int cap){int next=total+request;if(next>cap){next=cap;}total=next;return next-total+cap;}",
               "next-total", "nex-total"),
        repair("wrap_tone", A, "int pitches[12]; int note(int key,bool invert){int chroma=key%12;if(invert){chroma=11-chroma;}else{key++;}return pitches[chroma];}",
               "pitches[chroma]", "pitches[choma]"),
        repair("mix_counts", M, "int dilute(int first,int excess){if(excess<=0){return first;}int blended=first;while(excess>0){excess--;blended/=2;}return blended;}",
               "return blended;", "return;"),
        repair("stall_counter", D, "bool live(int retries,bool stable){bool passed=stable;for(int j=0;j<retries;j++){if(!passed){return false;}}bool allowed=passed;return allowed;}",
               "allowed=passed", "allowed=retries"),
        repair("printer_dimensions", F, "float paper(char tag,int count,bool portrait){if(portrait){return count*2.5;}return count;}float print(char code,bool upright,int quantity){return paper(code,quantity,upright);}",
               "paper(code,quantity,upright)", "paper(quantity,upright,code)"),
        repair("weigh_depth", V, "float scale=2.0;float weigh(float load,int depth){float adjusted=load*scale;{int depth=1;adjusted+=depth;}return adjusted/depth;}",
               "adjusted/depth", "adjustd/depth"),
        repair("rotor_grades", A, "int cells[10];int rotate(int r,int adv){int cycle=r+adv;for(int k=0;k<2;k++){cycle%=10;}if(cycle<0){return -1;}return cells[cycle];}",
               "cells[cycle]", "cells[cyle]"),
        control("training_guarded_lower", "int bulbs[8];int pulse(int signal){for(int j=6;j>=-1;j--){if(j<0){break;}bulbs[j]=signal+j;}return bulbs[1];}"),
    ],
    "selection": [
        repair("later_pick", V, "int pick(int current,int goal,bool repeat){int delta=goal-current; if(repeat){current+=delta;}else{delta++;}return current-delta;}",
               "current-delta", "current-deta"),
        repair("mixed_palette", A, "int colors[24];int hue(int shade,int tint){int code=shade*3+tint;if(code>23){code%=24;}if(code<0){code=0;}return colors[code];}",
               "colors[code]", "colors[cod]"),
        repair("ledger_open", D, "bool charge(int rows,bool opened){bool due=opened;while(rows>5){rows-=5;if(!due){return false;}}bool admitted=due;return admitted && rows>0;}",
               "admitted=due", "admitted=rows"),
        repair("warning_lookup", F, "int rate(int span,int offset,bool valid){if(valid){return span-offset;}return 0;}int warn(int n,bool flag){int diff=n-1;if(diff<0){return -1;}return rate(n,diff,flag);}",
               "rate(n,diff,flag)", "rate(n,dif,flag)"),
        repair("map_rollback", C, "int lamps[6];int darken(int state){for(int j=5;j>-1;j--){lamps[j]=state%3;state-=2;}return lamps[5];}", "j>-1", "j>=-1", kind="logic"),
    ],
    "calibration": [
        repair("valve_trim", V, "int valve(int pressure,int target,int kick){int margin=target-pressure;while(kick>0){target+=2;kick--;}if(pressure>target){return 0;}return margin-pressure;}",
               "margin-pressure", "margn-pressure"),
        repair("floor_pattern", A, "int planks[32];int floor(int row,int col){int shift=row*7+col;if(shift<0){return 0;}return planks[shift]+row*row;}",
               "planks[shift]", "planks[shft]"),
        repair("relay_delay", D, "bool relay(int count,bool emergency){bool armed=emergency;if(count<0){armed=false;}bool enabled=armed;for(int k=0;k<count;k++){if(enabled){return k>0;}}return false;}",
               "enabled=armed", "enabled=count"),
        repair("denoise", M, "int squash(int value,int steps){int best=value;while(steps>0){if(best>40){best/=2;}else{best-=1;}steps--;}return best;}",
               "return best;", "return;"),
        control("calibration_switch", "int cutoff(int ticks,int stay,bool stop){if(stop){return stay;}int estimate=ticks*stay;while(estimate>8){estimate/=2;}return ticks;}"),
        control("calibration_unknown", "int settle(int low,int high,bool check){if(check && low>high){return mark;}return low*high;}", True),
        repair("rail_status", C, "int rails[11];int reset(int offset){for(int n=8;n>-1;n--){rails[n]=n-offset;offset++;}return rails[2];}", "n>-1", "n>=-1", kind="logic"),
    ],
    "development": [
        repair("branch_dispatch", A, "int registers[15];int reverse(int shift){int result=shift;for(int i=14;i>=0;i--){int val=registers[i];if(val<0){result-=val;}else{result+=val;}}return result;}",
               "registers[i]", "registers[i-1]", kind="logic"),
        control("development_guard", "int drum[16];int trim(int start){for(int j=12;j>=-1;j--){if(j<0){return drum[6];}drum[j]=start*3;}return drum[0];}"),
    ],
}


if __name__ == "__main__":
    store(DEVELOPMENT, PARTITIONS)
