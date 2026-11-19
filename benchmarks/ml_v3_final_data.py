"""Post-freeze final fixtures. The training script does not load this module."""
import json

from .ml_v3_data import FINAL, A, C, D, F, L, M, O, R, V, X, control, repair

REVISION = "4812c213a2647e2034ad5ac78155ce9265cdd171"
SPECS = f"https://github.com/exercism/problem-specifications/blob/{REVISION}"


def adapted(slug, *args, **kwargs):
    return {**repair(*args, **kwargs), "provenance": "Original Mini-C exercise adapted from Exercism task description",
            "external_task": f"{SPECS}/exercises/{slug}/description.md", "license": "MIT",
            "license_url": f"{SPECS}/LICENSE"}


def spec(description, expression):
    return {"natural": {"description": description}, "explicit": {"return_expression": expression}}


def build():
    rows = [
        repair("barcode_ramp", C,
               "int marks[11]; int decode(int bias){int answer=bias;for(int n=0;n<11;n++){int digit=marks[n];if(digit>0){answer+=digit;}} return answer;}",
               "n<11", "n<=11", **L),
        repair("shifted_port", A,
               "int ports[13]; int update(int mask){for(int phase=0;phase<13;phase++){ports[phase]=mask%16;mask/=2;}return mask;}",
               "ports[phase]", "ports[phase-1]", **L),
        repair("ticket_adjustment", R,
               "int ticket(int base,int discount,bool approved){int reduced=base-discount;if(reduced<0){return 0;}if(approved){return reduced;}return reduced;}",
               "}return reduced;}", "}return base;}", **L),
        repair("layout_mirror", O,
               "int layout(int first,int middle,int last,int padding){int a=first+padding;int b=middle+padding;int c=last+padding;if(c<a){return c;}return a+b+c;}",
               "last+padding", "last-padding", **L),
        repair("log_update", X,
               "int flips[7]; int gaps[8]; int chart(){for(int j=0;j<7;j++){flips[j]=j-1;}for(int k=0;k<8;k++){gaps[k]=k*2;}return flips[0]+gaps[7];}",
               "j<7;j++){flips[j]=j-1;}for(int k=0;k<8;k++){gaps[k]",
               "j<=7;j++){flips[j]=j-1;}for(int k=0;k<8;k++){gaps[k+1]", **L),
        repair("ice_report", F,
               "bool reading(int station,char mode,bool on){if(mode=='?'){return false;}return station>0 && on;} bool publish(char token,bool enabled,int station){return reading(station,token,enabled);}",
               "reading(station,token,enabled)", "reading(token,enabled,station)"),
        repair("reset_shift", D,
               "bool set(int amount,bool ready,int phase){while(phase>0){amount*=2;phase--;} if(amount<0){return false;} bool chosen=ready;return chosen || phase==1;}",
               "chosen=ready", "chosen=amount"),
        repair("terminal_dispatch", V,
               "int dispatch(int base,int end,bool hold){int total=base+end; {int end=total*2;if(end<0){return base;}} if(hold){total-=1;}return total;}",
               "return total;", "return totl;"),
        repair("joined_alpha", M,
               "int alpha(int signal,int key){for(int j=0;j<3;j++){if(signal==key){break;}signal-=j;}signal+=key;return signal;}",
               "return signal;", "return;"),
        repair("cell_selection", A,
               "int logs[21]; int point(int offset,int skip){if(offset<0){offset=0;} while(skip<0){skip++;}return logs[offset];}", "logs[offset]", "logs[skip]", **L,
               **spec("return the element of logs at index offset", "logs[offset]")),
        repair("exclusion_band", C,
               "bool pass(int level,int upper,int lower){while(level<0){level+=2;}if(upper<=lower){upper=lower+1;}return level>lower && level<upper;}",
               "level>lower && level<upper", "level>=lower && level<=upper", **L,
               **spec("return whether level is between lower and upper exclusive", "level>lower && level<upper")),
        repair("negated_latch", C,
               "bool settle(bool armed,bool locked){return !(armed == locked);}", "!(armed == locked)", "armed == locked", **L,
               **spec("return whether not (armed is equal to locked)", "!(armed == locked)")),
        repair("charged_meter", O,
               "int fee(int delivered,int prior){int cents=delivered/2; return cents+(prior);}",
               "cents+(prior)", "cents-(prior)", **L,
               **spec("return the accumulator cents plus prior", "cents+(prior)")),
        repair("ordered_blend", F,
               "int blend(int left,int right){return left*3+right;} int pick(int weight,int value){return blend(weight,value);}",
               "blend(weight,value)", "blend(value,weight)", **L,
               natural={"function":"pick","description":"return the result of calling blend with weight and value"},
               explicit={"function":"pick","return_expression":"blend(weight,value)"}),
        repair("join_boundary", C,
               "bool range(int input,int near,int far,bool enabled){if(!enabled){return false;}return input>=near && input<=far;}",
               "input>=near && input<=far", "input>=near || input<=far", **L,
               natural={"description":"return whether input is between near and far inclusive","return_ordinal":2},
               explicit={"return_expression":"input>=near && input<=far","return_ordinal":2}),
        adapted("armstrong-numbers", "armstrong_partial_digit_power", C,
                "bool armstrong3(int n){if(n<100 || n>999){return false;} int left=n/100;int mid=n/10%10;int right=n%10;int sum=left*left*left+mid*mid*mid+right*right*right;return sum==n;}",
                "sum==n", "sum!=n", **L),
        adapted("resistor-color-duo", "resistor_numeric_lookup", A,
                "int bands[10]; int code(int first,int second){if(first<0 || second<0 || first>9 || second>9){return -1;}return bands[first]*10+bands[second];}",
                "+bands[second]", "+bands[first]", **L),
        adapted("series", "series_numeric_slice_cell", O,
                "int digits[16]; int slice_digit(int begin,int width,int cell){if(cell<0 || cell>=width || begin+width>16){return -1;}return digits[begin+cell];}",
                "begin+cell", "begin-cell", **L),
        control("control_source_quota", "int quota(int capacity,int count,bool reserve){if(reserve){capacity-=1;}int score=capacity*count;capacity--;return capacity;}"),
        control("control_boundary_break", "int bank[15];int deposit(int s){for(int i=0;i<=15;i++){if(i>=15){continue;}bank[i]=s*i;}return bank[0];}"),
        control("control_countdown", "int cells[6];int take(){int sum=0;for(int x=5;x>=0;x--){sum+=cells[x];}return sum;}"),
        control("control_intentional_rollover", "int calc(int base,int bump,int gate){int hi=base+bump;if(hi>=gate){return hi;}else{base-=gate;}return base;}"),
        control("control_conversion", "float ratio(float a,int b,bool safe){if(!safe || b==0){return 0;}return a/b;}"),
        control("control_shadow_ring", "int shift(int pos,int limit){int reserve=pos+1;while(pos<limit){int reserve=limit-pos;if(reserve==0){return pos;}pos++;}return reserve;}"),
        control("ambiguous_identifier", "int resolve(int upper,int lower){if(upper==lower){return upper;}return marked+3;}", True),
        control("ambiguous_operator", "int resolve_rate(int units,int rate,int change){int base=units*rate;if(base<10){return base+change;}return base-change;}", True),
    ]
    return {"version": 1, "cases": [{**row, "split": "final"} for row in rows]}


if __name__ == "__main__":
    FINAL.write_text(json.dumps(build(), indent=2) + "\n")
