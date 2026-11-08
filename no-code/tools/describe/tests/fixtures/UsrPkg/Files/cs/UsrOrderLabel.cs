using System;
using System.Globalization;
using Terrasoft.Core;
using Terrasoft.Core.Configuration;

namespace Terrasoft.Configuration
{
	/* The label format lives here so the listener, the process and the service share it.
	   Braces in this comment { } and an apostrophe: don't count them. */

	public enum UsrLabelStyle
	{
		Short = 0,
		Padded = 1
	}

	public interface IUsrOrderLabel
	{
		string Build(string type, int seq);
	}

	public static class UsrOrderLabel
	{
		public const int PadWidth = 4;
		private static readonly string Separator = "-";
		public static UsrLabelStyle Style { get; set; } = UsrLabelStyle.Padded;

		public static string Build(string type, int seq) {
			string head = (type ?? "").ToUpperInvariant();
			string tail = Style == UsrLabelStyle.Padded ? seq.ToString(CultureInfo.InvariantCulture).PadLeft(PadWidth, '0') : seq.ToString(CultureInfo.InvariantCulture);
			return head + Separator + tail; // "PARCEL-0007"
		}

		public static bool IsLabel(string text) => text != null && text.Contains(Separator);

		public static int MaxLength(UserConnection userConnection) {
			int configured = (int)SysSettings.GetValue(userConnection, "UsrLabelMaxLength", 50);
			return configured > 0 ? configured : 50;
		}

		private class Cache
		{
			public string Last;
			public void Remember(string label) { Last = label; }
		}
	}
}
