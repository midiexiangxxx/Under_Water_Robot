//***************************************************//
//STM32F103ʵ�ֹ��� 1.��ȿ�������PID��Ҫ�Ե���
//                  2.ǰ���ٶȿ�����
//                  2.��ת�ٶȿ�����
//
//�������������ʽ���ַ��������£�
//P_depth	I_depth		D_depth		a_depth 	v_x 	v_p 	pwm_max
//
//���У���v_x��ֵΪ0~100�����������ʻ��
//		         100~200��������ǰ��ʻ��
//���У���v_p��ֵΪ0~100����������ʱ����ת��
//		         100~200��������˳ʱ����ת��
//���У�pwm_max = 100ʱ�����������������Դﵽ��ǿ����100%��
//		pwm_max = xʱ�����������������Դﵽx%��
//***************************************************//

#include "include.h"

PID depth_pid;
int v_x = 0, v_p = 0, pwm_max = 0;

//************** Parameter of depth_pid *************//
int P_depth = 0, I_depth = 0, D_depth = 0;
int a_depth = 0;		

float depth;	int depth1 = 0, depth2 = 0;

float pwm_depth = 0;

//***************************************************//
int pwm_limit(int in)
{
	if(in < -pwm_max) in = -pwm_max;
	else if(in > pwm_max) in = pwm_max;
	return in * 5 + 1500;
}

int main(void)
{	
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO, ENABLE);
	GPIO_PinRemapConfig(GPIO_Remap_SWJ_JTAGDisable ,ENABLE);//����JTAG ���� SWD
	delay_init();
	////   		    
	PID_init(&depth_pid, 0, 0, 0, 1);
	pwm_init();
	trans_others_init(1, 115200);
	trans_others_init(2, 115200);

	while(1)
	{
		if(trans_others_R(2, &depth1, &depth2, 0, 0, 0, 0, 0, 0, 0, 0))
		{
			depth = depth1 + 0.01 * depth2;
		}		
		if(trans_others_R(1, &P_depth, &I_depth, &D_depth, &a_depth, &v_x, &v_p, &pwm_max, 0, 0, 0))
		{
			v_x -= 100, v_p -= 100;
			PID_init(&depth_pid, P_depth, I_depth, D_depth, 0);
			printf("P_depth = %d\r\n", P_depth);
			printf("I_depth = %d\r\n", I_depth);
			printf("D_depth = %d\r\n", D_depth);
			printf("a_depth = %d\r\n", a_depth);
			printf("v_x = %d\r\n", v_x);
			printf("v_y = %d\r\n", v_p);
			printf("pwm_max = %d\r\n", pwm_max);
			printf("depth = %.2f\r\n\r\n\r\n", depth);
		}
		
		pwm_depth = PID_calc1(&depth_pid, depth, a_depth);
		TIM_SetCompare1(TIM3, pwm_limit(pwm_depth));
		TIM_SetCompare2(TIM3, pwm_limit(pwm_depth));
		
		TIM_SetCompare1(TIM4, pwm_limit(v_x + v_p));
		TIM_SetCompare2(TIM4, pwm_limit(v_x - v_p));
		TIM_SetCompare3(TIM4, pwm_limit(v_x - v_p));
		TIM_SetCompare4(TIM4, pwm_limit(v_x + v_p));
	}
}