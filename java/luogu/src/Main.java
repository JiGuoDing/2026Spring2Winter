import java.util.ArrayList;
import java.util.List;

// TIP 要<b>运行</b>代码，请按 <shortcut actionId="Run"/> 或
// 点击装订区域中的 <icon src="AllIcons.Actions.Execute"/> 图标。
public class Main {
    public static void main(String[] args) {
        List list = new ArrayList();
        list.add("Hello, World!");
        list.add(0);
        list.add(1.1);

        for (Object item : list) {
            System.out.println(item);
        }
    }
}